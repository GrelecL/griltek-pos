"""Hospitality service: orders, KDS, table management, materialise to Sale."""
import uuid
from datetime import datetime, timezone
from decimal import Decimal
from typing import Any

from pydantic import BaseModel, ConfigDict
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.hospitality import FloorArea, Order, OrderLine, Table
from app.models.pos import Payment, Sale, SaleLine

# ── schemas ───────────────────────────────────────────────────────────────────

class OrderLineCreate(BaseModel):
    product_id: uuid.UUID
    product_name: str
    plu: str
    qty: Decimal
    unit_price: Decimal
    vat_rate: Decimal
    course: int | None = None
    kds_station: str | None = None
    note: str | None = None
    modifiers: list[dict[str, Any]] = []


class OrderCreate(BaseModel):
    location_id: uuid.UUID
    table_id: uuid.UUID | None = None
    user_id: uuid.UUID
    service_type: str = "eat_in"
    covers: int = 1
    pager_number: str | None = None
    note: str | None = None
    lines: list[OrderLineCreate] = []


class TableCreate(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    floor_area_id: uuid.UUID
    number: str
    capacity: int = 4
    pos_x: int = 0
    pos_y: int = 0


class FloorAreaCreate(BaseModel):
    location_id: uuid.UUID
    name: str
    sort_order: int = 0


# ── helpers ───────────────────────────────────────────────────────────────────

def _line_total(qty: Decimal, unit_price: Decimal) -> Decimal:
    return (qty * unit_price).quantize(Decimal("0.01"))


def _build_order_line(data: OrderLineCreate) -> OrderLine:
    return OrderLine(
        id=uuid.uuid4(),
        product_id=data.product_id,
        product_name=data.product_name,
        plu=data.plu,
        qty=data.qty,
        unit_price=data.unit_price,
        vat_rate=data.vat_rate,
        line_total=_line_total(data.qty, data.unit_price),
        course=data.course,
        kds_station=data.kds_station,
        note=data.note,
        modifiers=data.modifiers,
    )


# ── floor areas & tables ──────────────────────────────────────────────────────

async def create_floor_area(db: AsyncSession, data: FloorAreaCreate) -> FloorArea:
    area = FloorArea(id=uuid.uuid4(), **data.model_dump())
    db.add(area)
    await db.flush()
    return area


async def create_table(db: AsyncSession, data: TableCreate) -> Table:
    table = Table(id=uuid.uuid4(), **data.model_dump())
    db.add(table)
    await db.flush()
    return table


async def list_tables(db: AsyncSession, location_id: uuid.UUID) -> list[Table]:
    result = await db.execute(
        select(Table)
        .join(FloorArea)
        .where(FloorArea.location_id == location_id)
        .options(selectinload(Table.floor_area))
    )
    return list(result.scalars().all())


async def set_table_status(db: AsyncSession, table_id: uuid.UUID, status: str) -> Table | None:
    result = await db.execute(select(Table).where(Table.id == table_id))
    table = result.scalar_one_or_none()
    if table:
        table.status = status
    return table


# ── orders ────────────────────────────────────────────────────────────────────

async def create_order(db: AsyncSession, data: OrderCreate) -> Order:
    order = Order(
        id=uuid.uuid4(),
        location_id=data.location_id,
        table_id=data.table_id,
        user_id=data.user_id,
        service_type=data.service_type,
        covers=data.covers,
        pager_number=data.pager_number,
        note=data.note,
        status="open",
    )
    db.add(order)
    await db.flush()
    for ld in data.lines:
        line = _build_order_line(ld)
        line.order_id = order.id
        db.add(line)
    if data.table_id:
        await set_table_status(db, data.table_id, "occupied")
    return order


async def get_order(db: AsyncSession, order_id: uuid.UUID) -> Order | None:
    result = await db.execute(
        select(Order)
        .where(Order.id == order_id)
        .options(selectinload(Order.lines))
    )
    return result.scalar_one_or_none()


async def list_open_orders(db: AsyncSession, location_id: uuid.UUID) -> list[Order]:
    result = await db.execute(
        select(Order)
        .where(Order.location_id == location_id, Order.status == "open")
        .options(selectinload(Order.lines))
    )
    return list(result.scalars().all())


async def add_order_lines(db: AsyncSession, order_id: uuid.UUID, lines: list[OrderLineCreate]) -> Order | None:
    order = await get_order(db, order_id)
    if not order or order.status != "open":
        return None
    for ld in lines:
        line = _build_order_line(ld)
        line.order_id = order.id
        db.add(line)
    return order


async def fire_course(db: AsyncSession, order_id: uuid.UUID, course: int) -> int:
    """Fire a course: set all pending lines for this course to in_kitchen."""
    now = datetime.now(timezone.utc)
    result = await db.execute(
        select(OrderLine).where(
            OrderLine.order_id == order_id,
            OrderLine.course == course,
            OrderLine.kds_status == "pending",
        )
    )
    lines = list(result.scalars().all())
    for line in lines:
        line.kds_status = "in_kitchen"
        line.fired_at = now
    return len(lines)


async def update_kds_status(db: AsyncSession, line_id: uuid.UUID, status: str) -> OrderLine | None:
    result = await db.execute(select(OrderLine).where(OrderLine.id == line_id))
    line = result.scalar_one_or_none()
    if not line:
        return None
    now = datetime.now(timezone.utc)
    line.kds_status = status
    if status == "ready":
        line.ready_at = now
    elif status == "served":
        line.served_at = now
    return line


async def get_kds_lines(db: AsyncSession, location_id: uuid.UUID, station: str | None = None) -> list[OrderLine]:
    """Lines currently visible on KDS (pending or in_kitchen)."""
    q = (
        select(OrderLine)
        .join(Order)
        .where(
            Order.location_id == location_id,
            Order.status == "open",
            OrderLine.kds_status.in_(["in_kitchen", "ready"]),
        )
    )
    if station:
        q = q.where(OrderLine.kds_station == station)
    result = await db.execute(q)
    return list(result.scalars().all())


# ── materialise order → sale ──────────────────────────────────────────────────

async def materialise_order(
    db: AsyncSession,
    order_id: uuid.UUID,
    cash_session_id: uuid.UUID,
    user_id: uuid.UUID,
    payments: list[dict[str, Any]],
) -> Sale:
    order = await get_order(db, order_id)
    if not order:
        raise ValueError("Order not found")
    if order.status != "open":
        raise ValueError("Order already closed")

    subtotal = sum(l.line_total for l in order.lines)
    vat_total = sum(
        (l.line_total * l.vat_rate / (1 + l.vat_rate)).quantize(Decimal("0.01"))
        for l in order.lines
    )

    sale = Sale(
        id=uuid.uuid4(),
        transaction_uuid=uuid.uuid4(),
        cash_session_id=cash_session_id,
        location_id=order.location_id,
        user_id=user_id,
        sale_type="sale",
        status="completed",
        subtotal=subtotal,
        discount_total=Decimal("0"),
        vat_total=vat_total,
        total=subtotal,
    )
    db.add(sale)
    await db.flush()

    for ol in order.lines:
        vat_amount = (ol.line_total * ol.vat_rate / (1 + ol.vat_rate)).quantize(Decimal("0.01"))
        db.add(SaleLine(
            id=uuid.uuid4(),
            sale_id=sale.id,
            product_id=ol.product_id,
            product_name=ol.product_name,
            plu=ol.plu,
            qty=ol.qty,
            unit_price=ol.unit_price,
            vat_rate=ol.vat_rate,
            line_total=ol.line_total,
            vat_amount=vat_amount,
            discount_pct=Decimal("0"),
            discount_amount=Decimal("0"),
            modifiers=ol.modifiers,
        ))

    for p in payments:
        db.add(Payment(
            id=uuid.uuid4(),
            sale_id=sale.id,
            method=p["method"],
            amount=Decimal(str(p["amount"])),
            status="completed",
        ))

    order.status = "closed"
    order.sale_id = sale.id
    if order.table_id:
        await set_table_status(db, order.table_id, "free")

    return sale
