"""Reports service: sales, stock, fiscal, payment breakdown, dashboard."""
import csv
import io
import uuid
from datetime import datetime
from decimal import Decimal
from typing import Any

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.catalog import Product
from app.models.fiscal import FiscalRecord
from app.models.pos import Payment, Sale, SaleLine
from app.models.warehouse import StockItem, StockMovement

# ── dashboard ─────────────────────────────────────────────────────────────────

async def dashboard_summary(
    db: AsyncSession,
    location_id: uuid.UUID,
    date_from: datetime,
    date_to: datetime,
) -> dict[str, Any]:
    """Key metrics for the backoffice dashboard."""
    sales_q = select(
        func.count(Sale.id).label("count"),
        func.coalesce(func.sum(Sale.total), 0).label("revenue"),
    ).where(
        Sale.location_id == location_id,
        Sale.sale_type == "sale",
        Sale.status == "completed",
        Sale.completed_at >= date_from,
        Sale.completed_at <= date_to,
    )
    sales_result = (await db.execute(sales_q)).one()

    returns_q = select(
        func.count(Sale.id).label("count"),
        func.coalesce(func.sum(Sale.total), 0).label("total"),
    ).where(
        Sale.location_id == location_id,
        Sale.sale_type == "return",
        Sale.completed_at >= date_from,
        Sale.completed_at <= date_to,
    )
    returns_result = (await db.execute(returns_q)).one()

    pending_fiscal = (await db.execute(
        select(func.count(FiscalRecord.id)).where(FiscalRecord.status == "pending")
    )).scalar() or 0

    return {
        "period": {"from": date_from.isoformat(), "to": date_to.isoformat()},
        "sales": {"count": sales_result.count, "revenue": str(sales_result.revenue)},
        "returns": {"count": returns_result.count, "total": str(returns_result.total)},
        "net_revenue": str(Decimal(str(sales_result.revenue)) - Decimal(str(returns_result.total))),
        "pending_fiscal": pending_fiscal,
    }


# ── sales report ──────────────────────────────────────────────────────────────

async def sales_report(
    db: AsyncSession,
    location_id: uuid.UUID,
    date_from: datetime,
    date_to: datetime,
) -> list[dict[str, Any]]:
    """Per-sale summary rows."""
    result = await db.execute(
        select(Sale)
        .where(
            Sale.location_id == location_id,
            Sale.completed_at >= date_from,
            Sale.completed_at <= date_to,
            Sale.deleted_at.is_(None),
        )
        .order_by(Sale.completed_at)
    )
    rows = []
    for sale in result.scalars().all():
        rows.append({
            "id": str(sale.id),
            "completed_at": sale.completed_at.isoformat(),
            "sale_type": sale.sale_type,
            "status": sale.status,
            "subtotal": str(sale.subtotal),
            "discount_total": str(sale.discount_total),
            "vat_total": str(sale.vat_total),
            "total": str(sale.total),
        })
    return rows


async def sales_by_product(
    db: AsyncSession,
    location_id: uuid.UUID,
    date_from: datetime,
    date_to: datetime,
) -> list[dict[str, Any]]:
    """Aggregate sales qty and revenue per product."""
    q = (
        select(
            SaleLine.plu,
            SaleLine.product_name,
            func.sum(SaleLine.qty).label("total_qty"),
            func.sum(SaleLine.line_total).label("total_revenue"),
            func.sum(SaleLine.vat_amount).label("total_vat"),
        )
        .join(Sale, Sale.id == SaleLine.sale_id)
        .where(
            Sale.location_id == location_id,
            Sale.sale_type == "sale",
            Sale.status == "completed",
            Sale.completed_at >= date_from,
            Sale.completed_at <= date_to,
        )
        .group_by(SaleLine.plu, SaleLine.product_name)
        .order_by(func.sum(SaleLine.line_total).desc())
    )
    result = await db.execute(q)
    return [
        {
            "plu": r.plu, "product_name": r.product_name,
            "total_qty": str(r.total_qty),
            "total_revenue": str(r.total_revenue),
            "total_vat": str(r.total_vat),
        }
        for r in result.all()
    ]


async def payment_method_breakdown(
    db: AsyncSession,
    location_id: uuid.UUID,
    date_from: datetime,
    date_to: datetime,
) -> list[dict[str, Any]]:
    """Revenue by payment method."""
    q = (
        select(
            Payment.method,
            func.count(Payment.id).label("count"),
            func.sum(Payment.amount).label("total"),
        )
        .join(Sale, Sale.id == Payment.sale_id)
        .where(
            Sale.location_id == location_id,
            Sale.completed_at >= date_from,
            Sale.completed_at <= date_to,
        )
        .group_by(Payment.method)
        .order_by(func.sum(Payment.amount).desc())
    )
    result = await db.execute(q)
    return [
        {"method": r.method, "count": r.count, "total": str(r.total)}
        for r in result.all()
    ]


async def vat_breakdown(
    db: AsyncSession,
    location_id: uuid.UUID,
    date_from: datetime,
    date_to: datetime,
) -> list[dict[str, Any]]:
    """VAT collected per rate."""
    q = (
        select(
            SaleLine.vat_rate,
            func.sum(SaleLine.line_total).label("taxable"),
            func.sum(SaleLine.vat_amount).label("vat"),
        )
        .join(Sale, Sale.id == SaleLine.sale_id)
        .where(
            Sale.location_id == location_id,
            Sale.sale_type == "sale",
            Sale.status == "completed",
            Sale.completed_at >= date_from,
            Sale.completed_at <= date_to,
        )
        .group_by(SaleLine.vat_rate)
        .order_by(SaleLine.vat_rate)
    )
    result = await db.execute(q)
    return [
        {"vat_rate": str(r.vat_rate), "taxable": str(r.taxable), "vat": str(r.vat)}
        for r in result.all()
    ]


# ── stock report ──────────────────────────────────────────────────────────────

async def stock_levels(
    db: AsyncSession,
    warehouse_id: uuid.UUID,
    low_stock_only: bool = False,
) -> list[dict[str, Any]]:
    """Current stock levels; optionally filter to items below min_stock."""
    q = (
        select(StockItem, Product)
        .join(Product, Product.id == StockItem.product_id)
        .where(StockItem.warehouse_id == warehouse_id)
    )
    result = await db.execute(q)
    rows = []
    for item, product in result.all():
        if low_stock_only and (item.min_stock is None or item.qty > item.min_stock):
            continue
        rows.append({
            "product_id": str(product.id),
            "plu": product.plu,
            "name": product.name,
            "qty": str(item.qty),
            "reserved_qty": str(item.reserved_qty),
            "available": str(item.qty - item.reserved_qty),
            "min_stock": str(item.min_stock) if item.min_stock is not None else None,
            "is_low": item.min_stock is not None and item.qty <= item.min_stock,
        })
    return rows


async def stock_movements_report(
    db: AsyncSession,
    warehouse_id: uuid.UUID,
    date_from: datetime,
    date_to: datetime,
) -> list[dict[str, Any]]:
    result = await db.execute(
        select(StockMovement)
        .where(
            StockMovement.warehouse_id == warehouse_id,
            StockMovement.occurred_at >= date_from,
            StockMovement.occurred_at <= date_to,
        )
        .order_by(StockMovement.occurred_at.desc())
    )
    return [
        {
            "id": str(m.id), "product_id": str(m.product_id),
            "movement_type": m.movement_type, "qty": str(m.qty),
            "occurred_at": m.occurred_at.isoformat(),
            "reference_id": str(m.reference_id) if m.reference_id else None,
            "reference_type": m.reference_type,
        }
        for m in result.scalars().all()
    ]


# ── fiscal report ─────────────────────────────────────────────────────────────

async def fiscal_report(
    db: AsyncSession,
    date_from: datetime,
    date_to: datetime,
) -> dict[str, Any]:
    q = select(
        FiscalRecord.status,
        func.count(FiscalRecord.id).label("count"),
    ).where(
        FiscalRecord.created_at >= date_from,
        FiscalRecord.created_at <= date_to,
    ).group_by(FiscalRecord.status)

    result = await db.execute(q)
    by_status = {r.status: r.count for r in result.all()}
    return {
        "confirmed": by_status.get("confirmed", 0),
        "pending": by_status.get("pending", 0),
        "failed": by_status.get("failed", 0),
        "skipped": by_status.get("skipped", 0),
        "total": sum(by_status.values()),
    }


# ── CSV export ────────────────────────────────────────────────────────────────

def rows_to_csv(rows: list[dict[str, Any]]) -> str:
    if not rows:
        return ""
    buf = io.StringIO()
    writer = csv.DictWriter(buf, fieldnames=rows[0].keys())
    writer.writeheader()
    writer.writerows(rows)
    return buf.getvalue()
