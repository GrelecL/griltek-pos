"""
Fiscal service — handles ZOI/EOR generation and FiscalRecord management.

When furs_enabled=False on the location: returns a "skipped" FiscalRecord immediately.
When furs_enabled=True: computes ZOI, calls FURS adapter, stores FiscalRecord.
When FURS call fails (offline): stores record with status="pending", EOR=None.
  Pending records must be confirmed later within the legal window (see docs/FURS.md).
"""
import uuid
from datetime import datetime, timezone
from decimal import Decimal

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.adapters.furs.adapter import FursInvoiceRequest, get_furs_adapter
from app.models.fiscal import FiscalCounter, FiscalRecord
from app.models.location import Location, LocationConfig


async def _next_sequence(db: AsyncSession, location_id: uuid.UUID,
                          business_premise_id: str, electronic_device_id: str) -> int:
    """Atomically increment and return the next fiscal sequence number."""
    result = await db.execute(
        select(FiscalCounter).where(
            FiscalCounter.location_id == location_id,
            FiscalCounter.business_premise_id == business_premise_id,
            FiscalCounter.electronic_device_id == electronic_device_id,
        )
    )
    counter = result.scalar_one_or_none()
    if not counter:
        counter = FiscalCounter(
            location_id=location_id,
            business_premise_id=business_premise_id,
            electronic_device_id=electronic_device_id,
            last_sequence=0,
        )
        db.add(counter)
        await db.flush()
    counter.last_sequence += 1
    counter.version += 1
    await db.flush()
    return counter.last_sequence


async def fiscalize_sale(
    db: AsyncSession,
    sale_id: uuid.UUID,
    location_id: uuid.UUID,
    invoice_amount: Decimal,
    issued_at: datetime | None = None,
) -> FiscalRecord:
    """
    Main entry point. Checks furs_enabled on LocationConfig.
    Returns FiscalRecord (status: confirmed | pending | skipped).
    """
    if issued_at is None:
        issued_at = datetime.now(timezone.utc)

    # load location + config
    loc_result = await db.execute(select(Location).where(Location.id == location_id))
    location = loc_result.scalar_one_or_none()

    cfg_result = await db.execute(select(LocationConfig).where(LocationConfig.location_id == location_id))
    config = cfg_result.scalar_one_or_none()

    # ── FURS disabled ────────────────────────────────────────────────────────
    if not config or not config.furs_enabled:
        record = FiscalRecord(
            sale_id=sale_id,
            location_id=location_id,
            invoice_number="N/A",
            business_premise_id="N/A",
            electronic_device_id="N/A",
            invoice_amount=invoice_amount,
            issued_at=issued_at,
            status="skipped",
        )
        db.add(record)
        await db.commit()
        await db.refresh(record)
        return record

    # ── FURS enabled ─────────────────────────────────────────────────────────
    business_premise_id = location.furs_business_premise_id or "PP001"
    electronic_device_id = "B1"  # TODO: per-device in Step 6
    tax_number = location.furs_tax_number or "00000000"

    seq = await _next_sequence(db, location_id, business_premise_id, electronic_device_id)
    invoice_number = f"{business_premise_id}-{electronic_device_id}-{seq}"

    adapter = get_furs_adapter()
    req = FursInvoiceRequest(
        tax_number=tax_number,
        issued_at=issued_at,
        invoice_number=invoice_number,
        business_premise_id=business_premise_id,
        electronic_device_id=electronic_device_id,
        invoice_amount=invoice_amount,
    )

    try:
        resp = adapter.confirm_invoice(req)
        record = FiscalRecord(
            sale_id=sale_id,
            location_id=location_id,
            invoice_number=invoice_number,
            business_premise_id=business_premise_id,
            electronic_device_id=electronic_device_id,
            invoice_amount=invoice_amount,
            tax_number=tax_number,
            issued_at=issued_at,
            zoi=resp.zoi,
            eor=resp.eor,
            status=resp.status,
            furs_request=resp.raw_request,
            furs_response=resp.raw_response,
            confirmed_at=datetime.now(timezone.utc) if resp.status == "confirmed" else None,
        )
    except Exception as e:
        # Network/FURS error → store ZOI-only record as pending
        from app.adapters.furs.zoi import compute_zoi_mock
        zoi = compute_zoi_mock(tax_number, issued_at, invoice_number,
                                business_premise_id, electronic_device_id, invoice_amount)
        record = FiscalRecord(
            sale_id=sale_id,
            location_id=location_id,
            invoice_number=invoice_number,
            business_premise_id=business_premise_id,
            electronic_device_id=electronic_device_id,
            invoice_amount=invoice_amount,
            tax_number=tax_number,
            issued_at=issued_at,
            zoi=zoi,
            eor=None,
            status="pending",
            error_message=str(e)[:500],
        )

    db.add(record)
    await db.commit()
    await db.refresh(record)
    return record


async def get_pending_records(db: AsyncSession, location_id: uuid.UUID) -> list[FiscalRecord]:
    """Return all pending (EOR not yet received) fiscal records for a location."""
    result = await db.execute(
        select(FiscalRecord).where(
            FiscalRecord.location_id == location_id,
            FiscalRecord.status == "pending",
        ).order_by(FiscalRecord.issued_at)
    )
    return list(result.scalars().all())


async def retry_pending(db: AsyncSession, record: FiscalRecord) -> FiscalRecord:
    """Retry a pending FiscalRecord — call FURS again to get EOR."""
    adapter = get_furs_adapter()
    req = FursInvoiceRequest(
        tax_number=record.tax_number or "00000000",
        issued_at=record.issued_at,
        invoice_number=record.invoice_number,
        business_premise_id=record.business_premise_id,
        electronic_device_id=record.electronic_device_id,
        invoice_amount=record.invoice_amount,
    )
    try:
        resp = adapter.confirm_invoice(req)
        record.eor = resp.eor
        record.status = resp.status
        record.furs_response = resp.raw_response
        record.confirmed_at = datetime.now(timezone.utc)
        record.error_message = None
    except Exception as e:
        record.error_message = str(e)[:500]

    record.version += 1
    await db.commit()
    await db.refresh(record)
    return record


async def get_fiscal_record_by_sale(db: AsyncSession, sale_id: uuid.UUID) -> FiscalRecord | None:
    result = await db.execute(select(FiscalRecord).where(FiscalRecord.sale_id == sale_id))
    return result.scalar_one_or_none()


async def list_fiscal_records(db: AsyncSession, location_id: uuid.UUID,
                               status: str | None = None, limit: int = 100) -> list[FiscalRecord]:
    q = select(FiscalRecord).where(FiscalRecord.location_id == location_id)
    if status:
        q = q.where(FiscalRecord.status == status)
    q = q.order_by(FiscalRecord.issued_at.desc()).limit(limit)
    result = await db.execute(q)
    return list(result.scalars().all())
