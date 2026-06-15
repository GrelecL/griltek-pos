import uuid

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

import app.services.tenant as svc
from app.core.db import get_db
from app.schemas.tenant import (
    LocationConfigRead,
    LocationConfigUpdate,
    LocationCreate,
    LocationRead,
    TenantCreate,
    TenantRead,
)

router = APIRouter(prefix="/tenants", tags=["tenants"])


@router.post("", response_model=TenantRead, status_code=201)
async def create_tenant(data: TenantCreate, db: AsyncSession = Depends(get_db)):
    return await svc.create_tenant(db, data)


@router.get("", response_model=list[TenantRead])
async def list_tenants(db: AsyncSession = Depends(get_db)):
    return await svc.list_tenants(db)


@router.get("/{tenant_id}", response_model=TenantRead)
async def get_tenant(tenant_id: uuid.UUID, db: AsyncSession = Depends(get_db)):
    obj = await svc.get_tenant(db, tenant_id)
    if not obj:
        raise HTTPException(404, "Tenant not found")
    return obj


@router.post("/{tenant_id}/locations", response_model=LocationRead, status_code=201)
async def create_location(tenant_id: uuid.UUID, data: LocationCreate, db: AsyncSession = Depends(get_db)):
    data.tenant_id = tenant_id
    return await svc.create_location(db, data)


@router.get("/{tenant_id}/locations", response_model=list[LocationRead])
async def list_locations(tenant_id: uuid.UUID, db: AsyncSession = Depends(get_db)):
    return await svc.list_locations(db, tenant_id)


@router.get("/locations/{location_id}/config", response_model=LocationConfigRead)
async def get_location_config(location_id: uuid.UUID, db: AsyncSession = Depends(get_db)):
    obj = await svc.get_location_config(db, location_id)
    if not obj:
        raise HTTPException(404, "LocationConfig not found")
    return obj


@router.patch("/locations/{location_id}/config", response_model=LocationConfigRead)
async def update_location_config(
    location_id: uuid.UUID, data: LocationConfigUpdate, db: AsyncSession = Depends(get_db)
):
    obj = await svc.update_location_config(db, location_id, data)
    if not obj:
        raise HTTPException(404, "LocationConfig not found")
    return obj
