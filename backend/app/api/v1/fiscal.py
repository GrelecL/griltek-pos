import uuid

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession

import app.services.fiscal as svc
from app.core.db import get_db
from app.schemas.fiscal import FiscalizeRequest, FiscalRecordRead

router = APIRouter(prefix="/fiscal", tags=["fiscal"])


@router.post("/fiscalize", response_model=FiscalRecordRead, status_code=201)
async def fiscalize(data: FiscalizeRequest, db: AsyncSession = Depends(get_db)):
    """Fiscalize a sale. Returns FiscalRecord (status: confirmed|pending|skipped)."""
    record = await svc.fiscalize_sale(
        db, data.sale_id, data.location_id, data.invoice_amount
    )
    return record


@router.get("/records", response_model=list[FiscalRecordRead])
async def list_records(
    location_id: uuid.UUID = Query(...),
    status: str | None = Query(None),
    limit: int = Query(100, le=500),
    db: AsyncSession = Depends(get_db),
):
    return await svc.list_fiscal_records(db, location_id, status, limit)


@router.get("/records/by-sale/{sale_id}", response_model=FiscalRecordRead)
async def get_by_sale(sale_id: uuid.UUID, db: AsyncSession = Depends(get_db)):
    obj = await svc.get_fiscal_record_by_sale(db, sale_id)
    if not obj:
        raise HTTPException(404, "FiscalRecord not found")
    return obj


@router.get("/pending", response_model=list[FiscalRecordRead])
async def list_pending(location_id: uuid.UUID = Query(...), db: AsyncSession = Depends(get_db)):
    """List all pending fiscal records (EOR not yet received) for offline retry."""
    return await svc.get_pending_records(db, location_id)


@router.post("/records/{record_id}/retry", response_model=FiscalRecordRead)
async def retry(record_id: uuid.UUID, db: AsyncSession = Depends(get_db)):
    """Retry EOR confirmation for a pending record."""
    from sqlalchemy import select

    from app.models.fiscal import FiscalRecord
    result = await db.execute(select(FiscalRecord).where(FiscalRecord.id == record_id))
    record = result.scalar_one_or_none()
    if not record:
        raise HTTPException(404, "FiscalRecord not found")
    if record.status != "pending":
        raise HTTPException(400, "Record is not pending")
    return await svc.retry_pending(db, record)
