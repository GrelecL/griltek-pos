import uuid

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

import app.services.procurement as svc
from app.core.db import get_db
from app.models.procurement import GoodsReceipt
from app.schemas.procurement import (
    GoodsReceiptCreate,
    GoodsReceiptRead,
    PurchaseOrderCreate,
    PurchaseOrderRead,
    StockTakeCreate,
    StockTakeLineInput,
    StockTakeRead,
    SupplierCreate,
    SupplierRead,
    SupplierUpdate,
    TransferCreate,
    TransferRead,
)

router = APIRouter(prefix="/procurement", tags=["procurement"])


# Suppliers
@router.post("/suppliers", response_model=SupplierRead, status_code=201)
async def create_supplier(data: SupplierCreate, db: AsyncSession = Depends(get_db)):
    return await svc.create_supplier(db, data)

@router.get("/suppliers", response_model=list[SupplierRead])
async def list_suppliers(tenant_id: uuid.UUID = Query(...), db: AsyncSession = Depends(get_db)):
    return await svc.list_suppliers(db, tenant_id)

@router.get("/suppliers/{supplier_id}", response_model=SupplierRead)
async def get_supplier(supplier_id: uuid.UUID, db: AsyncSession = Depends(get_db)):
    obj = await svc.get_supplier(db, supplier_id)
    if not obj:
        raise HTTPException(404, "Supplier not found")
    return obj

@router.patch("/suppliers/{supplier_id}", response_model=SupplierRead)
async def update_supplier(supplier_id: uuid.UUID, data: SupplierUpdate, db: AsyncSession = Depends(get_db)):
    obj = await svc.update_supplier(db, supplier_id, data)
    if not obj:
        raise HTTPException(404, "Supplier not found")
    return obj


# Purchase Orders
@router.post("/purchase-orders", response_model=PurchaseOrderRead, status_code=201)
async def create_purchase_order(data: PurchaseOrderCreate, db: AsyncSession = Depends(get_db)):
    return await svc.create_purchase_order(db, data)

@router.get("/purchase-orders", response_model=list[PurchaseOrderRead])
async def list_purchase_orders(tenant_id: uuid.UUID = Query(...), db: AsyncSession = Depends(get_db)):
    return await svc.list_purchase_orders(db, tenant_id)

@router.get("/purchase-orders/{order_id}", response_model=PurchaseOrderRead)
async def get_purchase_order(order_id: uuid.UUID, db: AsyncSession = Depends(get_db)):
    obj = await svc.get_purchase_order(db, order_id)
    if not obj:
        raise HTTPException(404, "PurchaseOrder not found")
    return obj

@router.post("/purchase-orders/{order_id}/confirm", response_model=PurchaseOrderRead)
async def confirm_purchase_order(order_id: uuid.UUID, db: AsyncSession = Depends(get_db)):
    obj = await svc.confirm_purchase_order(db, order_id)
    if not obj:
        raise HTTPException(400, "Cannot confirm order (not in draft status)")
    return obj

@router.post("/purchase-orders/{order_id}/cancel", response_model=PurchaseOrderRead)
async def cancel_purchase_order(order_id: uuid.UUID, db: AsyncSession = Depends(get_db)):
    obj = await svc.cancel_purchase_order(db, order_id)
    if not obj:
        raise HTTPException(400, "Cannot cancel order")
    return obj


# Goods Receipts
@router.post("/goods-receipts", response_model=GoodsReceiptRead, status_code=201)
async def create_goods_receipt(data: GoodsReceiptCreate, db: AsyncSession = Depends(get_db)):
    return await svc.create_goods_receipt(db, data)

@router.get("/goods-receipts/{receipt_id}", response_model=GoodsReceiptRead)
async def get_goods_receipt(receipt_id: uuid.UUID, db: AsyncSession = Depends(get_db)):
    result = await db.execute(
        select(GoodsReceipt).where(GoodsReceipt.id == receipt_id)
        .options(selectinload(GoodsReceipt.lines))
    )
    obj = result.scalar_one_or_none()
    if not obj:
        raise HTTPException(404, "GoodsReceipt not found")
    return obj


# Transfers
@router.post("/transfers", response_model=TransferRead, status_code=201)
async def create_transfer(data: TransferCreate, db: AsyncSession = Depends(get_db)):
    return await svc.create_transfer(db, data)

@router.get("/transfers", response_model=list[TransferRead])
async def list_transfers(tenant_id: uuid.UUID = Query(...), db: AsyncSession = Depends(get_db)):
    return await svc.list_transfers(db, tenant_id)

@router.get("/transfers/{transfer_id}", response_model=TransferRead)
async def get_transfer(transfer_id: uuid.UUID, db: AsyncSession = Depends(get_db)):
    obj = await svc.get_transfer(db, transfer_id)
    if not obj:
        raise HTTPException(404, "Transfer not found")
    return obj

@router.post("/transfers/{transfer_id}/complete", response_model=TransferRead)
async def complete_transfer(transfer_id: uuid.UUID, db: AsyncSession = Depends(get_db)):
    obj = await svc.complete_transfer(db, transfer_id)
    if not obj:
        raise HTTPException(400, "Cannot complete transfer (not in pending status)")
    return obj


# Stock Takes
@router.post("/stock-takes", response_model=StockTakeRead, status_code=201)
async def create_stock_take(data: StockTakeCreate, db: AsyncSession = Depends(get_db)):
    return await svc.create_stock_take(db, data)

@router.get("/stock-takes", response_model=list[StockTakeRead])
async def list_stock_takes(tenant_id: uuid.UUID = Query(...), db: AsyncSession = Depends(get_db)):
    return await svc.list_stock_takes(db, tenant_id)

@router.get("/stock-takes/{stock_take_id}", response_model=StockTakeRead)
async def get_stock_take(stock_take_id: uuid.UUID, db: AsyncSession = Depends(get_db)):
    obj = await svc.get_stock_take(db, stock_take_id)
    if not obj:
        raise HTTPException(404, "StockTake not found")
    return obj

@router.post("/stock-takes/{stock_take_id}/counts", response_model=StockTakeRead)
async def submit_counts(stock_take_id: uuid.UUID, counts: list[StockTakeLineInput], db: AsyncSession = Depends(get_db)):
    obj = await svc.submit_counts(db, stock_take_id, counts)
    if not obj:
        raise HTTPException(400, "Cannot submit counts")
    return obj

@router.post("/stock-takes/{stock_take_id}/complete", response_model=StockTakeRead)
async def complete_stock_take(stock_take_id: uuid.UUID, db: AsyncSession = Depends(get_db)):
    obj = await svc.complete_stock_take(db, stock_take_id)
    if not obj:
        raise HTTPException(400, "Cannot complete stock take (must be in counting status)")
    return obj
