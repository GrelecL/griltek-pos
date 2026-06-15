import uuid
from datetime import datetime, timezone
from decimal import Decimal

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.procurement import (
    GoodsReceipt,
    GoodsReceiptLine,
    PurchaseOrder,
    PurchaseOrderLine,
    StockTake,
    StockTakeLine,
    Supplier,
    Transfer,
    TransferLine,
)
from app.models.warehouse import StockItem, StockMovement
from app.schemas.procurement import (
    GoodsReceiptCreate,
    PurchaseOrderCreate,
    StockTakeCreate,
    StockTakeLineInput,
    SupplierCreate,
    SupplierUpdate,
    TransferCreate,
)

# ── Supplier ──────────────────────────────────────────────────────────────────

async def create_supplier(db: AsyncSession, data: SupplierCreate) -> Supplier:
    obj = Supplier(**data.model_dump())
    db.add(obj)
    await db.commit()
    await db.refresh(obj)
    return obj

async def get_supplier(db: AsyncSession, supplier_id: uuid.UUID) -> Supplier | None:
    result = await db.execute(select(Supplier).where(Supplier.id == supplier_id, Supplier.deleted_at.is_(None)))
    return result.scalar_one_or_none()

async def list_suppliers(db: AsyncSession, tenant_id: uuid.UUID) -> list[Supplier]:
    result = await db.execute(
        select(Supplier).where(Supplier.tenant_id == tenant_id, Supplier.deleted_at.is_(None))
        .order_by(Supplier.name)
    )
    return list(result.scalars().all())

async def update_supplier(db: AsyncSession, supplier_id: uuid.UUID, data: SupplierUpdate) -> Supplier | None:
    obj = await get_supplier(db, supplier_id)
    if not obj:
        return None
    for k, v in data.model_dump(exclude_none=True).items():
        setattr(obj, k, v)
    obj.version += 1
    await db.commit()
    await db.refresh(obj)
    return obj


# ── PurchaseOrder ─────────────────────────────────────────────────────────────

async def create_purchase_order(db: AsyncSession, data: PurchaseOrderCreate) -> PurchaseOrder:
    lines_data = data.lines
    order = PurchaseOrder(**data.model_dump(exclude={"lines"}))
    db.add(order)
    await db.flush()
    for line in lines_data:
        db.add(PurchaseOrderLine(order_id=order.id, **line.model_dump()))
    await db.commit()
    result = await db.execute(
        select(PurchaseOrder).where(PurchaseOrder.id == order.id)
        .options(selectinload(PurchaseOrder.lines))
    )
    return result.scalar_one()

async def get_purchase_order(db: AsyncSession, order_id: uuid.UUID) -> PurchaseOrder | None:
    result = await db.execute(
        select(PurchaseOrder).where(PurchaseOrder.id == order_id)
        .options(selectinload(PurchaseOrder.lines))
    )
    return result.scalar_one_or_none()

async def list_purchase_orders(db: AsyncSession, tenant_id: uuid.UUID) -> list[PurchaseOrder]:
    result = await db.execute(
        select(PurchaseOrder).where(PurchaseOrder.tenant_id == tenant_id, PurchaseOrder.deleted_at.is_(None))
        .options(selectinload(PurchaseOrder.lines))
        .order_by(PurchaseOrder.created_at.desc())
    )
    return list(result.scalars().all())

async def confirm_purchase_order(db: AsyncSession, order_id: uuid.UUID) -> PurchaseOrder | None:
    order = await get_purchase_order(db, order_id)
    if not order or order.status != "draft":
        return None
    order.status = "ordered"
    order.ordered_at = datetime.now(timezone.utc)
    order.version += 1
    await db.commit()
    await db.refresh(order)
    return order

async def cancel_purchase_order(db: AsyncSession, order_id: uuid.UUID) -> PurchaseOrder | None:
    order = await get_purchase_order(db, order_id)
    if not order or order.status in ("received", "cancelled"):
        return None
    order.status = "cancelled"
    order.version += 1
    await db.commit()
    await db.refresh(order)
    return order


# ── GoodsReceipt ──────────────────────────────────────────────────────────────

async def _upsert_stock(db: AsyncSession, product_id: uuid.UUID, warehouse_id: uuid.UUID, qty: Decimal) -> None:
    result = await db.execute(
        select(StockItem).where(StockItem.product_id == product_id, StockItem.warehouse_id == warehouse_id)
    )
    stock = result.scalar_one_or_none()
    if stock:
        stock.qty += qty
        stock.version += 1
    else:
        db.add(StockItem(product_id=product_id, warehouse_id=warehouse_id, qty=qty))


async def create_goods_receipt(db: AsyncSession, data: GoodsReceiptCreate) -> GoodsReceipt:
    lines_data = data.lines
    receipt = GoodsReceipt(**data.model_dump(exclude={"lines"}))
    db.add(receipt)
    await db.flush()

    for line in lines_data:
        db.add(GoodsReceiptLine(receipt_id=receipt.id, **line.model_dump()))
        # update PO line received qty
        result = await db.execute(select(PurchaseOrderLine).where(PurchaseOrderLine.id == line.order_line_id))
        po_line = result.scalar_one_or_none()
        if po_line:
            po_line.qty_received += line.qty_received
        # create stock movement
        db.add(StockMovement(
            product_id=line.product_id,
            warehouse_id=data.warehouse_id,
            movement_type="receipt",
            qty=line.qty_received,
            reference_id=receipt.id,
            reference_type="goods_receipt",
        ))
        await _upsert_stock(db, line.product_id, data.warehouse_id, line.qty_received)

    # update PO status
    result = await db.execute(
        select(PurchaseOrder).where(PurchaseOrder.id == data.order_id)
        .options(selectinload(PurchaseOrder.lines))
    )
    order = result.scalar_one_or_none()
    if order:
        all_received = all(ln.qty_received >= ln.qty_ordered for ln in order.lines)
        order.status = "received" if all_received else "partial"
        order.version += 1

    await db.commit()
    result = await db.execute(
        select(GoodsReceipt).where(GoodsReceipt.id == receipt.id)
        .options(selectinload(GoodsReceipt.lines))
    )
    return result.scalar_one()


# ── Transfer ──────────────────────────────────────────────────────────────────

async def create_transfer(db: AsyncSession, data: TransferCreate) -> Transfer:
    lines_data = data.lines
    transfer = Transfer(**data.model_dump(exclude={"lines"}))
    db.add(transfer)
    await db.flush()
    for line in lines_data:
        db.add(TransferLine(transfer_id=transfer.id, **line.model_dump()))
    await db.commit()
    result = await db.execute(
        select(Transfer).where(Transfer.id == transfer.id)
        .options(selectinload(Transfer.lines))
    )
    return result.scalar_one()

async def complete_transfer(db: AsyncSession, transfer_id: uuid.UUID) -> Transfer | None:
    result = await db.execute(
        select(Transfer).where(Transfer.id == transfer_id)
        .options(selectinload(Transfer.lines))
    )
    transfer = result.scalar_one_or_none()
    if not transfer or transfer.status != "pending":
        return None

    for line in transfer.lines:
        # out from source
        db.add(StockMovement(
            product_id=line.product_id,
            warehouse_id=transfer.from_warehouse_id,
            movement_type="transfer",
            qty=-line.qty,
            reference_id=transfer.id,
            reference_type="transfer",
        ))
        await _upsert_stock(db, line.product_id, transfer.from_warehouse_id, -line.qty)
        # in to destination
        db.add(StockMovement(
            product_id=line.product_id,
            warehouse_id=transfer.to_warehouse_id,
            movement_type="transfer",
            qty=line.qty,
            reference_id=transfer.id,
            reference_type="transfer",
        ))
        await _upsert_stock(db, line.product_id, transfer.to_warehouse_id, line.qty)

    transfer.status = "completed"
    transfer.transferred_at = datetime.now(timezone.utc)
    transfer.version += 1
    await db.commit()
    await db.refresh(transfer)
    return transfer

async def get_transfer(db: AsyncSession, transfer_id: uuid.UUID) -> Transfer | None:
    result = await db.execute(
        select(Transfer).where(Transfer.id == transfer_id)
        .options(selectinload(Transfer.lines))
    )
    return result.scalar_one_or_none()

async def list_transfers(db: AsyncSession, tenant_id: uuid.UUID) -> list[Transfer]:
    result = await db.execute(
        select(Transfer).where(Transfer.tenant_id == tenant_id, Transfer.deleted_at.is_(None))
        .options(selectinload(Transfer.lines))
        .order_by(Transfer.created_at.desc())
    )
    return list(result.scalars().all())


# ── StockTake ─────────────────────────────────────────────────────────────────

async def create_stock_take(db: AsyncSession, data: StockTakeCreate) -> StockTake:
    """Snapshot current StockItem qty into StockTakeLine.qty_system for the warehouse."""
    stock_take = StockTake(**data.model_dump())
    db.add(stock_take)
    await db.flush()

    result = await db.execute(
        select(StockItem).where(StockItem.warehouse_id == data.warehouse_id)
    )
    items = list(result.scalars().all())
    for item in items:
        db.add(StockTakeLine(
            stock_take_id=stock_take.id,
            product_id=item.product_id,
            qty_system=item.qty,
        ))
    await db.commit()
    result = await db.execute(
        select(StockTake).where(StockTake.id == stock_take.id)
        .options(selectinload(StockTake.lines))
    )
    return result.scalar_one()

async def get_stock_take(db: AsyncSession, stock_take_id: uuid.UUID) -> StockTake | None:
    result = await db.execute(
        select(StockTake).where(StockTake.id == stock_take_id)
        .options(selectinload(StockTake.lines))
    )
    return result.scalar_one_or_none()

async def submit_counts(db: AsyncSession, stock_take_id: uuid.UUID, counts: list[StockTakeLineInput]) -> StockTake | None:
    """Record counted quantities on StockTakeLines."""
    stock_take = await get_stock_take(db, stock_take_id)
    if not stock_take or stock_take.status not in ("open", "counting"):
        return None
    count_map = {c.product_id: c.qty_counted for c in counts}
    for line in stock_take.lines:
        if line.product_id in count_map:
            line.qty_counted = count_map[line.product_id]
            line.qty_difference = line.qty_counted - line.qty_system
    stock_take.status = "counting"
    stock_take.version += 1
    await db.commit()
    return await get_stock_take(db, stock_take_id)

async def complete_stock_take(db: AsyncSession, stock_take_id: uuid.UUID) -> StockTake | None:
    """Finalize stock take: generate adjustment StockMovements for differences."""
    stock_take = await get_stock_take(db, stock_take_id)
    if not stock_take or stock_take.status != "counting":
        return None

    for line in stock_take.lines:
        if line.qty_counted is not None and line.qty_difference != Decimal("0"):
            db.add(StockMovement(
                product_id=line.product_id,
                warehouse_id=stock_take.warehouse_id,
                movement_type="adjustment",
                qty=line.qty_difference,
                reference_id=stock_take.id,
                reference_type="stock_take",
                note="StockTake adjustment",
            ))
            await _upsert_stock(db, line.product_id, stock_take.warehouse_id, line.qty_difference)

    stock_take.status = "completed"
    stock_take.completed_at = datetime.now(timezone.utc)
    stock_take.version += 1
    await db.commit()
    await db.refresh(stock_take)
    return stock_take

async def list_stock_takes(db: AsyncSession, tenant_id: uuid.UUID) -> list[StockTake]:
    result = await db.execute(
        select(StockTake).where(StockTake.tenant_id == tenant_id, StockTake.deleted_at.is_(None))
        .options(selectinload(StockTake.lines))
        .order_by(StockTake.started_at.desc())
    )
    return list(result.scalars().all())
