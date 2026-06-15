"""Customer loyalty portal API — no staff auth required, customer JWT used."""
from __future__ import annotations

import uuid
from datetime import datetime
from decimal import Decimal
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Security
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from jose import JWTError
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.db import get_db
from app.models.coupon import Coupon
from app.services import customer_portal as portal_svc

router = APIRouter(prefix="/customer-portal", tags=["customer-portal"])
_bearer = HTTPBearer()


# ── auth helper ───────────────────────────────────────────────────────────────

def _require_customer(credentials: HTTPAuthorizationCredentials = Security(_bearer)) -> dict:
    try:
        return portal_svc.decode_customer_token(credentials.credentials)
    except JWTError:
        raise HTTPException(401, "Invalid or expired token")


# ── schemas ───────────────────────────────────────────────────────────────────

class RegisterRequest(BaseModel):
    tenant_slug: str
    phone: str | None = None
    email: str | None = None
    pin: str


class LoginRequest(BaseModel):
    tenant_slug: str
    phone: str | None = None
    email: str | None = None
    pin: str


class CouponCreate(BaseModel):
    tenant_id: uuid.UUID
    code: str | None = None
    name: str
    description: str | None = None
    discount_type: str
    discount_value: Decimal
    min_purchase: Decimal | None = None
    valid_from: datetime | None = None
    valid_until: datetime | None = None
    max_uses: int | None = None
    per_customer_limit: int = 1


# ── public endpoints ──────────────────────────────────────────────────────────

@router.post("/register", status_code=201)
async def register(body: RegisterRequest, db: AsyncSession = Depends(get_db)):
    try:
        token, customer = await portal_svc.register(
            db, body.tenant_slug, body.phone, body.email, body.pin
        )
    except ValueError as e:
        raise HTTPException(400, str(e))
    await db.commit()
    return {
        "token": token,
        "customer": {"id": str(customer.id), "name": customer.name, "email": customer.email},
    }


@router.post("/auth")
async def login(body: LoginRequest, db: AsyncSession = Depends(get_db)):
    try:
        token, customer = await portal_svc.login(
            db, body.tenant_slug, body.phone, body.email, body.pin
        )
    except ValueError as e:
        raise HTTPException(401, str(e))
    return {
        "token": token,
        "customer": {"id": str(customer.id), "name": customer.name, "email": customer.email},
    }


# ── protected endpoints ───────────────────────────────────────────────────────

@router.get("/me")
async def me(payload: dict = Depends(_require_customer), db: AsyncSession = Depends(get_db)):
    from app.models.customer import Customer
    customer_id = uuid.UUID(payload["sub"])
    result = await db.execute(select(Customer).where(Customer.id == customer_id))
    customer = result.scalar_one_or_none()
    if not customer:
        raise HTTPException(404, "Customer not found")
    return {
        "id": str(customer.id),
        "name": customer.name,
        "email": customer.email,
        "phone": customer.phone,
    }


@router.get("/loyalty")
async def loyalty(payload: dict = Depends(_require_customer), db: AsyncSession = Depends(get_db)):
    customer_id = uuid.UUID(payload["sub"])
    tenant_id = uuid.UUID(payload["tenant_id"])
    summary = await portal_svc.get_loyalty_summary(db, customer_id, tenant_id)
    return {**summary, "customer_qr": str(customer_id)}


@router.get("/receipts")
async def receipts(
    limit: int = 20,
    offset: int = 0,
    payload: dict = Depends(_require_customer),
    db: AsyncSession = Depends(get_db),
):
    customer_id = uuid.UUID(payload["sub"])
    return await portal_svc.get_receipts(db, customer_id, limit=limit, offset=offset)


@router.get("/receipts/{sale_id}")
async def receipt_detail(
    sale_id: uuid.UUID,
    payload: dict = Depends(_require_customer),
    db: AsyncSession = Depends(get_db),
):
    customer_id = uuid.UUID(payload["sub"])
    receipt = await portal_svc.get_receipt(db, customer_id, sale_id)
    if not receipt:
        raise HTTPException(404, "Receipt not found")
    return receipt


@router.get("/coupons")
async def coupons(payload: dict = Depends(_require_customer), db: AsyncSession = Depends(get_db)):
    customer_id = uuid.UUID(payload["sub"])
    tenant_id = uuid.UUID(payload["tenant_id"])
    return await portal_svc.get_available_coupons(db, customer_id, tenant_id)


# ── admin coupon management (staff endpoint, not customer-facing) ─────────────

@router.post("/coupons", status_code=201, tags=["admin"])
async def create_coupon(body: CouponCreate, db: AsyncSession = Depends(get_db)):
    import secrets
    code = body.code or secrets.token_urlsafe(8).upper()
    coupon = Coupon(
        id=uuid.uuid4(),
        tenant_id=body.tenant_id,
        code=code,
        name=body.name,
        description=body.description,
        discount_type=body.discount_type,
        discount_value=body.discount_value,
        min_purchase=body.min_purchase,
        valid_from=body.valid_from,
        valid_until=body.valid_until,
        max_uses=body.max_uses,
        per_customer_limit=body.per_customer_limit,
    )
    db.add(coupon)
    await db.commit()
    return {"id": str(coupon.id), "code": coupon.code, "name": coupon.name}
