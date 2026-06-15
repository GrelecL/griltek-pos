import uuid

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession

import app.services.auth as svc
from app.core.db import get_db
from app.schemas.auth import (
    PinLoginRequest,
    PinLoginResponse,
    RoleCreate,
    RoleRead,
    UserCreate,
    UserRead,
)

router = APIRouter(tags=["auth"])


@router.post("/roles", response_model=RoleRead, status_code=201)
async def create_role(data: RoleCreate, db: AsyncSession = Depends(get_db)):
    return await svc.create_role(db, data)


@router.get("/roles", response_model=list[RoleRead])
async def list_roles(
    tenant_id: uuid.UUID = Query(...), db: AsyncSession = Depends(get_db)
):
    return await svc.list_roles(db, tenant_id)


@router.post("/users", response_model=UserRead, status_code=201)
async def create_user(data: UserCreate, db: AsyncSession = Depends(get_db)):
    return await svc.create_user(db, data)


@router.get("/users", response_model=list[UserRead])
async def list_users(
    tenant_id: uuid.UUID = Query(...), db: AsyncSession = Depends(get_db)
):
    return await svc.list_users(db, tenant_id)


@router.get("/users/{user_id}", response_model=UserRead)
async def get_user(user_id: uuid.UUID, db: AsyncSession = Depends(get_db)):
    obj = await svc.get_user(db, user_id)
    if not obj:
        raise HTTPException(404, "User not found")
    return obj


@router.post("/auth/pin-login", response_model=PinLoginResponse)
async def pin_login(data: PinLoginRequest, db: AsyncSession = Depends(get_db)):
    result = await svc.pin_login(db, data.location_id, data.pin)
    if not result:
        raise HTTPException(401, "Invalid PIN or no access to this location")
    return result
