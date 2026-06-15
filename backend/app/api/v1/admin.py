"""Admin API: GDPR erasure, audit log, sync health."""
import uuid

from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.db import get_db
from app.models.audit import AuditLog
from app.services.gdpr import erase_customer

router = APIRouter(prefix="/admin", tags=["admin"])


# ── GDPR erasure ──────────────────────────────────────────────────────────────

class EraseRequest(BaseModel):
    requesting_user_id: uuid.UUID | None = None
    tenant_id: uuid.UUID | None = None


@router.delete("/customers/{customer_id}/pii")
async def gdpr_erase_customer(
    customer_id: uuid.UUID,
    body: EraseRequest,
    request: Request,
    db: AsyncSession = Depends(get_db),
):
    ok = await erase_customer(
        db,
        customer_id,
        requesting_user_id=body.requesting_user_id,
        tenant_id=body.tenant_id,
        ip_address=request.client.host if request.client else None,
    )
    if not ok:
        raise HTTPException(404, "Customer not found")
    await db.commit()
    return {"erased": True, "customer_id": str(customer_id)}


# ── Audit log ─────────────────────────────────────────────────────────────────

@router.get("/audit-log")
async def get_audit_log(
    tenant_id: uuid.UUID | None = None,
    action: str | None = None,
    limit: int = 100,
    db: AsyncSession = Depends(get_db),
):
    q = select(AuditLog).order_by(AuditLog.occurred_at.desc()).limit(limit)
    if tenant_id:
        q = q.where(AuditLog.tenant_id == tenant_id)
    if action:
        q = q.where(AuditLog.action == action)
    result = await db.execute(q)
    return [
        {
            "id": str(e.id),
            "occurred_at": e.occurred_at.isoformat(),
            "tenant_id": str(e.tenant_id) if e.tenant_id else None,
            "user_id": str(e.user_id) if e.user_id else None,
            "action": e.action,
            "resource_type": e.resource_type,
            "resource_id": e.resource_id,
            "ip_address": e.ip_address,
            "device_id": e.device_id,
            "detail": e.detail,
        }
        for e in result.scalars().all()
    ]


# ── Sync health ───────────────────────────────────────────────────────────────

@router.get("/sync-health")
async def sync_health(db: AsyncSession = Depends(get_db)):
    """
    Cloud-side sync health: counts pending fiscal records and unsynced
    stock movements as proxies for sync lag. Edge-side health comes from
    the store-server /sync/status endpoint.
    """
    from sqlalchemy import func

    from app.models.fiscal import FiscalRecord
    from app.models.warehouse import StockMovement

    pending_fiscal = (await db.execute(
        select(func.count(FiscalRecord.id)).where(FiscalRecord.status == "pending")
    )).scalar() or 0

    unsynced_movements = (await db.execute(
        select(func.count(StockMovement.id)).where(StockMovement.synced_at.is_(None))
    )).scalar() or 0

    return {
        "pending_fiscal_records": pending_fiscal,
        "unsynced_stock_movements": unsynced_movements,
        "status": "ok" if (pending_fiscal == 0 and unsynced_movements == 0) else "degraded",
    }
