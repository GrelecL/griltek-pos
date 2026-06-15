"""Electronic Shelf Labels API."""
from __future__ import annotations

import uuid

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.db import get_db
from app.services import esl as esl_svc

router = APIRouter(prefix="/esl", tags=["esl"])


class DeviceRegisterRequest(BaseModel):
    location_id: uuid.UUID
    esl_id: str
    product_id: uuid.UUID | None = None


class AssignProductRequest(BaseModel):
    product_id: uuid.UUID


class SyncLocationRequest(BaseModel):
    location_id: uuid.UUID
    tenant_id: uuid.UUID


def _device_out(d) -> dict:
    return {
        "id": str(d.id),
        "esl_id": d.esl_id,
        "location_id": str(d.location_id),
        "product_id": str(d.product_id) if d.product_id else None,
        "status": d.status,
        "last_synced_at": d.last_synced_at.isoformat() if d.last_synced_at else None,
        "last_price": str(d.last_price) if d.last_price is not None else None,
        "last_error": d.last_error,
    }


@router.post("/devices", status_code=201)
async def register_device(body: DeviceRegisterRequest, db: AsyncSession = Depends(get_db)):
    device = await esl_svc.register_device(db, body.location_id, body.esl_id, body.product_id)
    await db.commit()
    return _device_out(device)


@router.get("/devices")
async def list_devices(location_id: uuid.UUID, db: AsyncSession = Depends(get_db)):
    devices = await esl_svc.list_devices(db, location_id)
    return [_device_out(d) for d in devices]


@router.put("/devices/{device_id}/product")
async def assign_product(device_id: uuid.UUID, body: AssignProductRequest, db: AsyncSession = Depends(get_db)):
    device = await esl_svc.assign_product(db, device_id, body.product_id)
    await db.commit()
    return _device_out(device)


@router.post("/devices/{device_id}/sync")
async def sync_device(device_id: uuid.UUID, tenant_id: uuid.UUID, db: AsyncSession = Depends(get_db)):
    try:
        device = await esl_svc.sync_device(db, device_id, tenant_id)
    except ValueError as e:
        raise HTTPException(400, str(e))
    await db.commit()
    return _device_out(device)


@router.post("/sync")
async def sync_location(body: SyncLocationRequest, db: AsyncSession = Depends(get_db)):
    summary = await esl_svc.sync_location(db, body.location_id, body.tenant_id)
    await db.commit()
    return summary
