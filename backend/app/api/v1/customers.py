import uuid

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession

import app.services.customer as svc
from app.core.db import get_db
from app.schemas.customer import (
    CreditAccountCreate,
    CreditAccountRead,
    CustomerCreate,
    CustomerRead,
    CustomerUpdate,
)

router = APIRouter(prefix="/customers", tags=["customers"])


@router.post("", response_model=CustomerRead, status_code=201)
async def create_customer(data: CustomerCreate, db: AsyncSession = Depends(get_db)):
    return await svc.create_customer(db, data)


@router.get("", response_model=list[CustomerRead])
async def list_customers(
    tenant_id: uuid.UUID = Query(...),
    search: str | None = Query(None),
    db: AsyncSession = Depends(get_db),
):
    return await svc.list_customers(db, tenant_id, search)


@router.get("/{customer_id}", response_model=CustomerRead)
async def get_customer(customer_id: uuid.UUID, db: AsyncSession = Depends(get_db)):
    obj = await svc.get_customer(db, customer_id)
    if not obj:
        raise HTTPException(404, "Customer not found")
    return obj


@router.patch("/{customer_id}", response_model=CustomerRead)
async def update_customer(
    customer_id: uuid.UUID,
    data: CustomerUpdate,
    db: AsyncSession = Depends(get_db),
):
    obj = await svc.update_customer(db, customer_id, data)
    if not obj:
        raise HTTPException(404, "Customer not found")
    return obj


@router.post("/{customer_id}/credit-account", response_model=CreditAccountRead, status_code=201)
async def create_credit_account(
    customer_id: uuid.UUID,
    data: CreditAccountCreate,
    db: AsyncSession = Depends(get_db),
):
    data.customer_id = customer_id
    return await svc.create_credit_account(db, data)


@router.get("/{customer_id}/credit-account", response_model=CreditAccountRead)
async def get_credit_account(
    customer_id: uuid.UUID, db: AsyncSession = Depends(get_db)
):
    obj = await svc.get_credit_account(db, customer_id)
    if not obj:
        raise HTTPException(404, "Credit account not found")
    return obj
