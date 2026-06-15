import uuid
from datetime import datetime, timezone
from decimal import ROUND_HALF_UP, Decimal

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.pos import CashSession, Payment, Sale, SaleLine
from app.models.warehouse import StockMovement, Warehouse
from app.schemas.pos import (
    CashAdjustment,
    CashSessionClose,
    CashSessionOpen,
    PaymentCreate,
    SaleCreate,
    SaleLineCreate,
    XReport,
    ZReport,
)

# ── CashSession ───────────────────────────────────────────────────────────────

async def open_session(db: AsyncSession, data: CashSessionOpen) -> CashSession:
    session = CashSession(**data.model_dump())
    db.add(session)
    await db.commit()
    await db.refresh(session)
    return session


async def get_session(db: AsyncSession, session_id: uuid.UUID) -> CashSession | None:
    result = await db.execute(
        select(CashSession)
        .where(CashSession.id == session_id)
        .options(selectinload(CashSession.sales))
    )
    return result.scalar_one_or_none()


async def get_open_session(
    db: AsyncSession,
    location_id: uuid.UUID,
    device_id: uuid.UUID | None = None,
) -> CashSession | None:
    q = select(CashSession).where(
        CashSession.location_id == location_id,
        CashSession.status == "open",
    )
    if device_id:
        q = q.where(CashSession.device_id == device_id)
    result = await db.execute(q)
    return result.scalar_one_or_none()


async def cash_in(
    db: AsyncSession, session_id: uuid.UUID, data: CashAdjustment
) -> CashSession | None:
    session = await get_session(db, session_id)
    if not session or session.status != "open":
        return None
    session.cash_in += data.amount
    session.version += 1
    await db.commit()
    await db.refresh(session)
    return session


async def cash_out(
    db: AsyncSession, session_id: uuid.UUID, data: CashAdjustment
) -> CashSession | None:
    session = await get_session(db, session_id)
    if not session or session.status != "open":
        return None
    session.cash_out += data.amount
    session.version += 1
    await db.commit()
    await db.refresh(session)
    return session


async def close_session(
    db: AsyncSession, session_id: uuid.UUID, data: CashSessionClose
) -> CashSession | None:
    session = await get_session(db, session_id)
    if not session or session.status != "open":
        return None
    session.status = "closed"
    session.closing_float = data.closing_float
    session.closed_at = datetime.now(timezone.utc)
    if data.note:
        session.note = data.note
    session.version += 1
    await db.commit()
    await db.refresh(session)
    return session


def _round2(v: Decimal) -> Decimal:
    return v.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)


async def _build_x_report(db: AsyncSession, session: CashSession) -> dict:
    # Fetch all sales for session with payments loaded
    sales_result = await db.execute(
        select(Sale)
        .where(Sale.cash_session_id == session.id)
        .options(selectinload(Sale.payments))
    )
    all_sales = sales_result.scalars().all()

    sales_total = Decimal("0")
    returns_total = Decimal("0")
    sale_count = 0
    return_count = 0
    cash_sales = Decimal("0")
    card_sales = Decimal("0")

    for s in all_sales:
        if s.sale_type == "sale":
            sales_total += s.total
            sale_count += 1
            for p in s.payments:
                if p.method == "cash":
                    cash_sales += p.amount
                elif p.method in ("card", "sumup"):
                    card_sales += p.amount
        else:
            returns_total += s.total
            return_count += 1

    sales_total = _round2(sales_total)
    returns_total = _round2(returns_total)
    cash_sales = _round2(cash_sales)
    card_sales = _round2(card_sales)

    net_sales = _round2(sales_total - returns_total)
    other_sales = _round2(net_sales - cash_sales - card_sales)
    expected_cash = _round2(
        session.opening_float + cash_sales + session.cash_in - session.cash_out
    )

    return {
        "session_id": session.id,
        "generated_at": datetime.now(timezone.utc),
        "total_sales": sales_total,
        "total_returns": returns_total,
        "net_sales": net_sales,
        "cash_sales": cash_sales,
        "card_sales": card_sales,
        "other_sales": other_sales,
        "sale_count": sale_count,
        "return_count": return_count,
        "opening_float": session.opening_float,
        "cash_in": session.cash_in,
        "cash_out": session.cash_out,
        "expected_cash": expected_cash,
    }


async def x_report(db: AsyncSession, session_id: uuid.UUID) -> XReport | None:
    session = await get_session(db, session_id)
    if not session:
        return None
    data = await _build_x_report(db, session)
    return XReport(**data)


async def z_report(db: AsyncSession, session_id: uuid.UUID) -> ZReport | None:
    session = await get_session(db, session_id)
    if not session or session.status != "closed":
        return None
    data = await _build_x_report(db, session)
    data["closed_at"] = session.closed_at
    return ZReport(**data)


# ── Sale ──────────────────────────────────────────────────────────────────────

def _compute_line(
    qty: Decimal,
    unit_price: Decimal,
    vat_rate: Decimal,
    discount_pct: Decimal,
    discount_amount: Decimal,
) -> tuple[Decimal, Decimal]:
    """Return (line_total, vat_amount) both rounded to 4dp."""
    gross = qty * unit_price
    disc = gross * (discount_pct / Decimal("100")) + discount_amount
    net_incl_vat = gross - disc
    vat_amt = net_incl_vat * vat_rate / (Decimal("100") + vat_rate)
    return (
        net_incl_vat.quantize(Decimal("0.0001"), rounding=ROUND_HALF_UP),
        vat_amt.quantize(Decimal("0.0001"), rounding=ROUND_HALF_UP),
    )


async def _get_default_warehouse(
    db: AsyncSession, location_id: uuid.UUID
) -> uuid.UUID:
    result = await db.execute(
        select(Warehouse).where(
            Warehouse.location_id == location_id,
            Warehouse.is_default.is_(True),
            Warehouse.deleted_at.is_(None),
        )
    )
    wh = result.scalar_one_or_none()
    if wh:
        return wh.id
    result2 = await db.execute(
        select(Warehouse).where(
            Warehouse.location_id == location_id,
            Warehouse.deleted_at.is_(None),
        )
    )
    wh2 = result2.scalars().first()
    if wh2:
        return wh2.id
    return uuid.UUID("00000000-0000-0000-0000-000000000000")


async def create_sale(db: AsyncSession, data: SaleCreate) -> Sale:
    """Create sale with lines and payments. Idempotent by transaction_uuid."""
    # idempotency check
    existing = await db.execute(
        select(Sale).where(Sale.transaction_uuid == data.transaction_uuid)
    )
    if existing.scalar_one_or_none():
        result = await db.execute(
            select(Sale)
            .where(Sale.transaction_uuid == data.transaction_uuid)
            .options(selectinload(Sale.lines), selectinload(Sale.payments))
        )
        return result.scalar_one()

    subtotal = Decimal("0")
    discount_total = Decimal("0")
    vat_total = Decimal("0")
    sale_lines = []

    for line_data in data.lines:
        line_total, vat_amt = _compute_line(
            line_data.qty,
            line_data.unit_price,
            line_data.vat_rate,
            line_data.discount_pct,
            line_data.discount_amount,
        )
        disc = (
            line_data.qty * line_data.unit_price * (line_data.discount_pct / Decimal("100"))
            + line_data.discount_amount
        )
        subtotal += (line_data.qty * line_data.unit_price).quantize(
            Decimal("0.0001"), rounding=ROUND_HALF_UP
        )
        discount_total += disc.quantize(Decimal("0.0001"), rounding=ROUND_HALF_UP)
        vat_total += vat_amt
        sale_lines.append((line_data, line_total, vat_amt))

    total = _round2(subtotal - discount_total)

    sale = Sale(
        transaction_uuid=data.transaction_uuid,
        cash_session_id=data.cash_session_id,
        location_id=data.location_id,
        device_id=data.device_id,
        user_id=data.user_id,
        customer_id=data.customer_id,
        sale_type=data.sale_type,
        note=data.note,
        subtotal=_round2(subtotal),
        discount_total=_round2(discount_total),
        vat_total=_round2(vat_total),
        total=total,
    )
    db.add(sale)
    await db.flush()

    warehouse_id = await _get_default_warehouse(db, data.location_id)

    for line_data, line_total, vat_amt in sale_lines:
        db.add(
            SaleLine(
                sale_id=sale.id,
                product_id=line_data.product_id,
                product_name=line_data.product_name,
                plu=line_data.plu,
                qty=line_data.qty,
                unit_price=line_data.unit_price,
                vat_rate=line_data.vat_rate,
                discount_pct=line_data.discount_pct,
                discount_amount=line_data.discount_amount,
                line_total=_round2(line_total),
                vat_amount=_round2(vat_amt),
                modifiers=line_data.modifiers,
            )
        )
        # stock movement
        multiplier = Decimal("1") if data.sale_type == "return" else Decimal("-1")
        db.add(
            StockMovement(
                product_id=line_data.product_id,
                warehouse_id=warehouse_id,
                movement_type="sale" if data.sale_type == "sale" else "return",
                qty=multiplier * line_data.qty,
                reference_id=sale.id,
                reference_type="sale",
            )
        )

    for pay_data in data.payments:
        db.add(
            Payment(
                sale_id=sale.id,
                **pay_data.model_dump(),
            )
        )

    # update session cash_in for cash payments on sales
    if data.sale_type == "sale":
        for pay in data.payments:
            if pay.method == "cash":
                session = await db.get(CashSession, data.cash_session_id)
                if session:
                    session.cash_in += pay.amount

    await db.commit()
    result = await db.execute(
        select(Sale)
        .where(Sale.id == sale.id)
        .options(selectinload(Sale.lines), selectinload(Sale.payments))
    )
    return result.scalar_one()


async def get_sale(db: AsyncSession, sale_id: uuid.UUID) -> Sale | None:
    result = await db.execute(
        select(Sale)
        .where(Sale.id == sale_id)
        .options(selectinload(Sale.lines), selectinload(Sale.payments))
    )
    return result.scalar_one_or_none()


async def list_sales(
    db: AsyncSession,
    location_id: uuid.UUID | None = None,
    session_id: uuid.UUID | None = None,
    limit: int = 100,
) -> list[Sale]:
    q = select(Sale).options(
        selectinload(Sale.lines), selectinload(Sale.payments)
    )
    if location_id:
        q = q.where(Sale.location_id == location_id)
    if session_id:
        q = q.where(Sale.cash_session_id == session_id)
    q = q.order_by(Sale.completed_at.desc()).limit(limit)
    result = await db.execute(q)
    return list(result.scalars().all())


async def void_sale(
    db: AsyncSession, sale_id: uuid.UUID, user_id: uuid.UUID
) -> Sale | None:
    """Create a return (storno) for an existing sale."""
    original = await get_sale(db, sale_id)
    if not original or original.sale_type != "sale":
        return None
    return_data = SaleCreate(
        transaction_uuid=uuid.uuid4(),
        cash_session_id=original.cash_session_id,
        location_id=original.location_id,
        device_id=original.device_id,
        user_id=user_id,
        customer_id=original.customer_id,
        sale_type="return",
        note=f"Storno of {original.id}",
        lines=[
            SaleLineCreate(
                product_id=ln.product_id,
                product_name=ln.product_name,
                plu=ln.plu,
                qty=ln.qty,
                unit_price=ln.unit_price,
                vat_rate=ln.vat_rate,
                discount_pct=ln.discount_pct,
                discount_amount=ln.discount_amount,
                modifiers=ln.modifiers,
            )
            for ln in original.lines
        ],
        payments=[
            PaymentCreate(
                method=p.method,
                amount=p.amount,
            )
            for p in original.payments
        ],
    )
    return_sale = await create_sale(db, return_data)
    return_sale.original_sale_id = original.id
    await db.commit()
    await db.refresh(return_sale)
    return return_sale
