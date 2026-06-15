"""Reports API: dashboard, sales, stock, fiscal, CSV export."""
import uuid
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, Query, Response
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.db import get_db
from app.services.reports import (
    dashboard_summary,
    fiscal_report,
    payment_method_breakdown,
    rows_to_csv,
    sales_by_product,
    sales_report,
    stock_levels,
    stock_movements_report,
    vat_breakdown,
)

router = APIRouter(prefix="/reports", tags=["reports"])


def _parse_dt(s: str | None, default: datetime) -> datetime:
    if not s:
        return default
    return datetime.fromisoformat(s).replace(tzinfo=timezone.utc)


@router.get("/dashboard")
async def api_dashboard(
    location_id: uuid.UUID,
    date_from: str | None = Query(None, description="ISO date, e.g. 2026-01-01"),
    date_to: str | None = Query(None),
    db: AsyncSession = Depends(get_db),
):
    now = datetime.now(timezone.utc)
    df = _parse_dt(date_from, now.replace(hour=0, minute=0, second=0, microsecond=0))
    dt = _parse_dt(date_to, now)
    return await dashboard_summary(db, location_id, df, dt)


@router.get("/sales")
async def api_sales_report(
    location_id: uuid.UUID,
    date_from: str | None = Query(None),
    date_to: str | None = Query(None),
    fmt: str = Query("json", description="json | csv"),
    db: AsyncSession = Depends(get_db),
):
    now = datetime.now(timezone.utc)
    df = _parse_dt(date_from, now.replace(hour=0, minute=0, second=0, microsecond=0))
    dt = _parse_dt(date_to, now)
    rows = await sales_report(db, location_id, df, dt)
    if fmt == "csv":
        return Response(rows_to_csv(rows), media_type="text/csv",
                        headers={"Content-Disposition": "attachment; filename=sales.csv"})
    return rows


@router.get("/sales/by-product")
async def api_sales_by_product(
    location_id: uuid.UUID,
    date_from: str | None = Query(None),
    date_to: str | None = Query(None),
    fmt: str = Query("json"),
    db: AsyncSession = Depends(get_db),
):
    now = datetime.now(timezone.utc)
    df = _parse_dt(date_from, now.replace(hour=0, minute=0, second=0, microsecond=0))
    dt = _parse_dt(date_to, now)
    rows = await sales_by_product(db, location_id, df, dt)
    if fmt == "csv":
        return Response(rows_to_csv(rows), media_type="text/csv",
                        headers={"Content-Disposition": "attachment; filename=sales_by_product.csv"})
    return rows


@router.get("/sales/payments")
async def api_payment_breakdown(
    location_id: uuid.UUID,
    date_from: str | None = Query(None),
    date_to: str | None = Query(None),
    db: AsyncSession = Depends(get_db),
):
    now = datetime.now(timezone.utc)
    df = _parse_dt(date_from, now.replace(hour=0, minute=0, second=0, microsecond=0))
    dt = _parse_dt(date_to, now)
    return await payment_method_breakdown(db, location_id, df, dt)


@router.get("/sales/vat")
async def api_vat_breakdown(
    location_id: uuid.UUID,
    date_from: str | None = Query(None),
    date_to: str | None = Query(None),
    db: AsyncSession = Depends(get_db),
):
    now = datetime.now(timezone.utc)
    df = _parse_dt(date_from, now.replace(hour=0, minute=0, second=0, microsecond=0))
    dt = _parse_dt(date_to, now)
    return await vat_breakdown(db, location_id, df, dt)


@router.get("/stock")
async def api_stock_levels(
    warehouse_id: uuid.UUID,
    low_stock_only: bool = Query(False),
    fmt: str = Query("json"),
    db: AsyncSession = Depends(get_db),
):
    rows = await stock_levels(db, warehouse_id, low_stock_only=low_stock_only)
    if fmt == "csv":
        return Response(rows_to_csv(rows), media_type="text/csv",
                        headers={"Content-Disposition": "attachment; filename=stock.csv"})
    return rows


@router.get("/stock/movements")
async def api_stock_movements(
    warehouse_id: uuid.UUID,
    date_from: str | None = Query(None),
    date_to: str | None = Query(None),
    fmt: str = Query("json"),
    db: AsyncSession = Depends(get_db),
):
    now = datetime.now(timezone.utc)
    df = _parse_dt(date_from, now.replace(hour=0, minute=0, second=0, microsecond=0))
    dt = _parse_dt(date_to, now)
    rows = await stock_movements_report(db, warehouse_id, df, dt)
    if fmt == "csv":
        return Response(rows_to_csv(rows), media_type="text/csv",
                        headers={"Content-Disposition": "attachment; filename=movements.csv"})
    return rows


@router.get("/fiscal")
async def api_fiscal_report(
    date_from: str | None = Query(None),
    date_to: str | None = Query(None),
    db: AsyncSession = Depends(get_db),
):
    now = datetime.now(timezone.utc)
    df = _parse_dt(date_from, now.replace(hour=0, minute=0, second=0, microsecond=0))
    dt = _parse_dt(date_to, now)
    return await fiscal_report(db, df, dt)
