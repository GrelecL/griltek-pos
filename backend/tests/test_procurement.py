import uuid
from decimal import Decimal

import pytest
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

import app.services.catalog as catalog_svc
import app.services.procurement as svc
import app.services.tenant as tenant_svc
import app.services.warehouse as wh_svc
from app.models.warehouse import StockMovement
from app.schemas.catalog import ProductCreate
from app.schemas.procurement import (
    GoodsReceiptCreate,
    GoodsReceiptLineCreate,
    POLineCreate,
    PurchaseOrderCreate,
    StockTakeCreate,
    StockTakeLineInput,
    SupplierCreate,
    SupplierUpdate,
    TransferCreate,
    TransferLineCreate,
)
from app.schemas.tenant import TenantCreate
from app.schemas.warehouse import WarehouseCreate

# ── Seed helpers ──────────────────────────────────────────────────────────────

async def make_tenant(db: AsyncSession) -> uuid.UUID:
    t = await tenant_svc.create_tenant(db, TenantCreate(name="Proc Tenant", slug=f"proc-{uuid.uuid4().hex[:6]}"))
    return t.id


async def make_product(db: AsyncSession, tenant_id: uuid.UUID, plu: str = "P1") -> uuid.UUID:
    p = await catalog_svc.create_product(db, ProductCreate(tenant_id=tenant_id, plu=plu, name=f"Prod {plu}"))
    return p.id


async def make_warehouse(db: AsyncSession, tenant_id: uuid.UUID, name: str = "Main") -> uuid.UUID:
    w = await wh_svc.create_warehouse(db, WarehouseCreate(tenant_id=tenant_id, name=name))
    return w.id


async def make_supplier(db: AsyncSession, tenant_id: uuid.UUID, name: str = "ACME") -> uuid.UUID:
    s = await svc.create_supplier(db, SupplierCreate(tenant_id=tenant_id, name=name))
    return s.id


# ── Supplier tests ────────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_create_supplier(db: AsyncSession):
    tid = await make_tenant(db)
    supplier = await svc.create_supplier(db, SupplierCreate(
        tenant_id=tid,
        name="ACME Corp",
        email="acme@example.com",
        phone="555-1234",
    ))
    assert supplier.id is not None
    assert supplier.name == "ACME Corp"
    assert supplier.email == "acme@example.com"
    assert supplier.is_active is True

    fetched = await svc.get_supplier(db, supplier.id)
    assert fetched is not None
    assert fetched.id == supplier.id


@pytest.mark.asyncio
async def test_update_supplier(db: AsyncSession):
    tid = await make_tenant(db)
    sid = await make_supplier(db, tid, "Old Name")

    updated = await svc.update_supplier(db, sid, SupplierUpdate(name="New Name", is_active=False))
    assert updated is not None
    assert updated.name == "New Name"
    assert updated.is_active is False
    assert updated.version == 2


# ── PurchaseOrder tests ───────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_create_purchase_order_with_lines(db: AsyncSession):
    tid = await make_tenant(db)
    sid = await make_supplier(db, tid)
    wid = await make_warehouse(db, tid)
    pid = await make_product(db, tid, "PO1")

    order = await svc.create_purchase_order(db, PurchaseOrderCreate(
        tenant_id=tid,
        supplier_id=sid,
        warehouse_id=wid,
        lines=[POLineCreate(product_id=pid, qty_ordered=Decimal("10"), unit_cost=Decimal("5.50"))],
    ))

    assert order.id is not None
    assert order.status == "draft"
    assert len(order.lines) == 1
    assert order.lines[0].qty_ordered == Decimal("10")
    assert order.lines[0].qty_received == Decimal("0")


@pytest.mark.asyncio
async def test_confirm_purchase_order(db: AsyncSession):
    tid = await make_tenant(db)
    sid = await make_supplier(db, tid)
    wid = await make_warehouse(db, tid)
    pid = await make_product(db, tid, "PO2")

    order = await svc.create_purchase_order(db, PurchaseOrderCreate(
        tenant_id=tid, supplier_id=sid, warehouse_id=wid,
        lines=[POLineCreate(product_id=pid, qty_ordered=Decimal("5"), unit_cost=Decimal("2"))],
    ))

    confirmed = await svc.confirm_purchase_order(db, order.id)
    assert confirmed is not None
    assert confirmed.status == "ordered"
    assert confirmed.ordered_at is not None

    # Cannot confirm again
    result = await svc.confirm_purchase_order(db, order.id)
    assert result is None


@pytest.mark.asyncio
async def test_cancel_purchase_order(db: AsyncSession):
    tid = await make_tenant(db)
    sid = await make_supplier(db, tid)
    wid = await make_warehouse(db, tid)
    pid = await make_product(db, tid, "PO3")

    order = await svc.create_purchase_order(db, PurchaseOrderCreate(
        tenant_id=tid, supplier_id=sid, warehouse_id=wid,
        lines=[POLineCreate(product_id=pid, qty_ordered=Decimal("3"), unit_cost=Decimal("1"))],
    ))

    cancelled = await svc.cancel_purchase_order(db, order.id)
    assert cancelled is not None
    assert cancelled.status == "cancelled"

    # Cannot cancel again
    result = await svc.cancel_purchase_order(db, order.id)
    assert result is None


# ── GoodsReceipt tests ────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_goods_receipt_updates_stock(db: AsyncSession):
    tid = await make_tenant(db)
    sid = await make_supplier(db, tid)
    wid = await make_warehouse(db, tid)
    pid = await make_product(db, tid, "GR1")

    order = await svc.create_purchase_order(db, PurchaseOrderCreate(
        tenant_id=tid, supplier_id=sid, warehouse_id=wid,
        lines=[POLineCreate(product_id=pid, qty_ordered=Decimal("10"), unit_cost=Decimal("3"))],
    ))
    po_line_id = order.lines[0].id

    receipt = await svc.create_goods_receipt(db, GoodsReceiptCreate(
        order_id=order.id,
        warehouse_id=wid,
        lines=[GoodsReceiptLineCreate(
            order_line_id=po_line_id,
            product_id=pid,
            qty_received=Decimal("10"),
            unit_cost=Decimal("3"),
        )],
    ))

    assert receipt.id is not None
    assert len(receipt.lines) == 1

    # StockItem updated
    stock = await wh_svc.get_stock_item(db, pid, wid)
    assert stock is not None
    assert stock.qty == Decimal("10")

    # StockMovement created
    movements_result = await db.execute(
        select(StockMovement).where(StockMovement.product_id == pid, StockMovement.warehouse_id == wid)
    )
    movements = list(movements_result.scalars().all())
    assert len(movements) == 1
    assert movements[0].movement_type == "receipt"
    assert movements[0].qty == Decimal("10")

    # PO line qty_received updated
    updated_order = await svc.get_purchase_order(db, order.id)
    assert updated_order.lines[0].qty_received == Decimal("10")

    # PO status -> received
    assert updated_order.status == "received"


@pytest.mark.asyncio
async def test_goods_receipt_partial(db: AsyncSession):
    tid = await make_tenant(db)
    sid = await make_supplier(db, tid)
    wid = await make_warehouse(db, tid)
    pid = await make_product(db, tid, "GR2")

    order = await svc.create_purchase_order(db, PurchaseOrderCreate(
        tenant_id=tid, supplier_id=sid, warehouse_id=wid,
        lines=[POLineCreate(product_id=pid, qty_ordered=Decimal("10"), unit_cost=Decimal("3"))],
    ))
    po_line_id = order.lines[0].id

    await svc.create_goods_receipt(db, GoodsReceiptCreate(
        order_id=order.id,
        warehouse_id=wid,
        lines=[GoodsReceiptLineCreate(
            order_line_id=po_line_id,
            product_id=pid,
            qty_received=Decimal("6"),
            unit_cost=Decimal("3"),
        )],
    ))

    updated_order = await svc.get_purchase_order(db, order.id)
    assert updated_order.status == "partial"
    assert updated_order.lines[0].qty_received == Decimal("6")


# ── Transfer tests ────────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_create_transfer(db: AsyncSession):
    tid = await make_tenant(db)
    wid1 = await make_warehouse(db, tid, "WH-A")
    wid2 = await make_warehouse(db, tid, "WH-B")
    pid = await make_product(db, tid, "TR1")

    transfer = await svc.create_transfer(db, TransferCreate(
        tenant_id=tid,
        from_warehouse_id=wid1,
        to_warehouse_id=wid2,
        lines=[TransferLineCreate(product_id=pid, qty=Decimal("5"))],
    ))

    assert transfer.id is not None
    assert transfer.status == "pending"
    assert len(transfer.lines) == 1
    assert transfer.lines[0].qty == Decimal("5")


@pytest.mark.asyncio
async def test_complete_transfer_moves_stock(db: AsyncSession):
    tid = await make_tenant(db)
    wid1 = await make_warehouse(db, tid, "WH-SRC")
    wid2 = await make_warehouse(db, tid, "WH-DST")
    pid = await make_product(db, tid, "TR2")

    # Seed stock in source warehouse
    from app.schemas.warehouse import StockMovementCreate
    await wh_svc.create_movement(db, StockMovementCreate(
        product_id=pid, warehouse_id=wid1, movement_type="receipt", qty=Decimal("20"),
    ))

    transfer = await svc.create_transfer(db, TransferCreate(
        tenant_id=tid,
        from_warehouse_id=wid1,
        to_warehouse_id=wid2,
        lines=[TransferLineCreate(product_id=pid, qty=Decimal("8"))],
    ))

    completed = await svc.complete_transfer(db, transfer.id)
    assert completed is not None
    assert completed.status == "completed"
    assert completed.transferred_at is not None

    # Source stock decremented
    src_stock = await wh_svc.get_stock_item(db, pid, wid1)
    assert src_stock.qty == Decimal("12")

    # Destination stock created
    dst_stock = await wh_svc.get_stock_item(db, pid, wid2)
    assert dst_stock is not None
    assert dst_stock.qty == Decimal("8")

    # Cannot complete again
    result = await svc.complete_transfer(db, transfer.id)
    assert result is None


# ── StockTake tests ───────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_stock_take_snapshot(db: AsyncSession):
    tid = await make_tenant(db)
    wid = await make_warehouse(db, tid)
    pid1 = await make_product(db, tid, "ST1")
    pid2 = await make_product(db, tid, "ST2")

    from app.schemas.warehouse import StockMovementCreate
    await wh_svc.create_movement(db, StockMovementCreate(
        product_id=pid1, warehouse_id=wid, movement_type="receipt", qty=Decimal("15"),
    ))
    await wh_svc.create_movement(db, StockMovementCreate(
        product_id=pid2, warehouse_id=wid, movement_type="receipt", qty=Decimal("30"),
    ))

    stock_take = await svc.create_stock_take(db, StockTakeCreate(tenant_id=tid, warehouse_id=wid))

    assert stock_take.id is not None
    assert stock_take.status == "open"
    assert len(stock_take.lines) == 2

    qty_map = {line.product_id: line.qty_system for line in stock_take.lines}
    assert qty_map[pid1] == Decimal("15")
    assert qty_map[pid2] == Decimal("30")


@pytest.mark.asyncio
async def test_stock_take_submit_counts(db: AsyncSession):
    tid = await make_tenant(db)
    wid = await make_warehouse(db, tid)
    pid = await make_product(db, tid, "ST3")

    from app.schemas.warehouse import StockMovementCreate
    await wh_svc.create_movement(db, StockMovementCreate(
        product_id=pid, warehouse_id=wid, movement_type="receipt", qty=Decimal("10"),
    ))

    stock_take = await svc.create_stock_take(db, StockTakeCreate(tenant_id=tid, warehouse_id=wid))

    updated = await svc.submit_counts(db, stock_take.id, [
        StockTakeLineInput(product_id=pid, qty_counted=Decimal("9")),
    ])

    assert updated is not None
    assert updated.status == "counting"
    line = updated.lines[0]
    assert line.qty_counted == Decimal("9")
    assert line.qty_difference == Decimal("-1")


@pytest.mark.asyncio
async def test_stock_take_complete_generates_adjustments(db: AsyncSession):
    tid = await make_tenant(db)
    wid = await make_warehouse(db, tid)
    pid = await make_product(db, tid, "ST4")

    from app.schemas.warehouse import StockMovementCreate
    await wh_svc.create_movement(db, StockMovementCreate(
        product_id=pid, warehouse_id=wid, movement_type="receipt", qty=Decimal("10"),
    ))

    stock_take = await svc.create_stock_take(db, StockTakeCreate(tenant_id=tid, warehouse_id=wid))

    await svc.submit_counts(db, stock_take.id, [
        StockTakeLineInput(product_id=pid, qty_counted=Decimal("8")),
    ])

    completed = await svc.complete_stock_take(db, stock_take.id)
    assert completed is not None
    assert completed.status == "completed"
    assert completed.completed_at is not None

    # StockItem adjusted
    stock = await wh_svc.get_stock_item(db, pid, wid)
    assert stock.qty == Decimal("8")

    # Adjustment StockMovement created
    movements_result = await db.execute(
        select(StockMovement).where(
            StockMovement.product_id == pid,
            StockMovement.warehouse_id == wid,
            StockMovement.movement_type == "adjustment",
        )
    )
    adj_movements = list(movements_result.scalars().all())
    assert len(adj_movements) == 1
    assert adj_movements[0].qty == Decimal("-2")

    # Cannot complete again
    result = await svc.complete_stock_take(db, stock_take.id)
    assert result is None
