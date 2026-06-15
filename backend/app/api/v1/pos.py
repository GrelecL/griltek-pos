import uuid
from decimal import Decimal
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

import app.services.pos as svc
from app.core.db import get_db
from app.models.coupon import Coupon, CouponRedemption
from app.models.customer import Customer
from app.models.payments import LoyaltyAccount, LoyaltyProgram
from app.schemas.pos import (
    CashAdjustment,
    CashSessionClose,
    CashSessionOpen,
    CashSessionRead,
    SaleCreate,
    SaleRead,
    XReport,
    ZReport,
)

router = APIRouter(tags=["pos"])


@router.post("/cash-sessions", response_model=CashSessionRead, status_code=201)
async def open_session(data: CashSessionOpen, db: AsyncSession = Depends(get_db)):
    return await svc.open_session(db, data)


@router.get("/cash-sessions/{session_id}", response_model=CashSessionRead)
async def get_session(session_id: uuid.UUID, db: AsyncSession = Depends(get_db)):
    obj = await svc.get_session(db, session_id)
    if not obj:
        raise HTTPException(404, "Session not found")
    return obj


@router.post("/cash-sessions/{session_id}/cash-in", response_model=CashSessionRead)
async def cash_in(
    session_id: uuid.UUID,
    data: CashAdjustment,
    db: AsyncSession = Depends(get_db),
):
    obj = await svc.cash_in(db, session_id, data)
    if not obj:
        raise HTTPException(400, "Session not open")
    return obj


@router.post("/cash-sessions/{session_id}/cash-out", response_model=CashSessionRead)
async def cash_out(
    session_id: uuid.UUID,
    data: CashAdjustment,
    db: AsyncSession = Depends(get_db),
):
    obj = await svc.cash_out(db, session_id, data)
    if not obj:
        raise HTTPException(400, "Session not open")
    return obj


@router.post("/cash-sessions/{session_id}/close", response_model=CashSessionRead)
async def close_session(
    session_id: uuid.UUID,
    data: CashSessionClose,
    db: AsyncSession = Depends(get_db),
):
    obj = await svc.close_session(db, session_id, data)
    if not obj:
        raise HTTPException(400, "Session not open")
    return obj


@router.get("/cash-sessions/{session_id}/x-report", response_model=XReport)
async def x_report(session_id: uuid.UUID, db: AsyncSession = Depends(get_db)):
    obj = await svc.x_report(db, session_id)
    if not obj:
        raise HTTPException(404, "Session not found")
    return obj


@router.get("/cash-sessions/{session_id}/z-report", response_model=ZReport)
async def z_report(session_id: uuid.UUID, db: AsyncSession = Depends(get_db)):
    obj = await svc.z_report(db, session_id)
    if not obj:
        raise HTTPException(400, "Session must be closed for Z-report")
    return obj


@router.post("/sales", response_model=SaleRead, status_code=201)
async def create_sale(data: SaleCreate, db: AsyncSession = Depends(get_db)):
    return await svc.create_sale(db, data)


@router.get("/sales", response_model=list[SaleRead])
async def list_sales(
    location_id: uuid.UUID | None = Query(None),
    session_id: uuid.UUID | None = Query(None),
    limit: int = Query(100, le=500),
    db: AsyncSession = Depends(get_db),
):
    return await svc.list_sales(db, location_id, session_id, limit)


@router.get("/sales/{sale_id}", response_model=SaleRead)
async def get_sale(sale_id: uuid.UUID, db: AsyncSession = Depends(get_db)):
    obj = await svc.get_sale(db, sale_id)
    if not obj:
        raise HTTPException(404, "Sale not found")
    return obj


@router.post("/sales/{sale_id}/void", response_model=SaleRead)
async def void_sale(
    sale_id: uuid.UUID,
    user_id: uuid.UUID = Query(...),
    db: AsyncSession = Depends(get_db),
):
    obj = await svc.void_sale(db, sale_id, user_id)
    if not obj:
        raise HTTPException(400, "Cannot void this sale")
    return obj


# ── Customer QR scan at POS ───────────────────────────────────────────────────

@router.get("/customer-scan/{customer_id}")
async def customer_scan(customer_id: uuid.UUID, db: AsyncSession = Depends(get_db)):
    """Cashier scans customer's loyalty QR — returns customer info + loyalty summary."""
    result = await db.execute(select(Customer).where(Customer.id == customer_id))
    customer = result.scalar_one_or_none()
    if not customer:
        raise HTTPException(404, "Customer not found")

    prog_result = await db.execute(
        select(LoyaltyProgram).where(
            LoyaltyProgram.tenant_id == customer.tenant_id,
            LoyaltyProgram.is_active == True,
        )
    )
    program = prog_result.scalar_one_or_none()

    loyalty_summary = None
    if program:
        acc_result = await db.execute(
            select(LoyaltyAccount).where(
                LoyaltyAccount.program_id == program.id,
                LoyaltyAccount.customer_id == customer_id,
            )
        )
        account = acc_result.scalar_one_or_none()
        if account:
            loyalty_summary = {
                "points_balance": account.points_balance,
                "tier": account.tier,
                "redeem_value": str(
                    (Decimal(str(account.points_balance)) * program.redeem_rate).quantize(Decimal("0.01"))
                ),
            }

    return {
        "id": str(customer.id),
        "name": customer.name,
        "phone": customer.phone,
        "email": customer.email,
        "loyalty": loyalty_summary,
    }


# ── Coupon validation at POS ──────────────────────────────────────────────────

class ValidateCouponRequest(BaseModel):
    code: str
    customer_id: uuid.UUID | None = None
    sale_total: Decimal = Decimal("0")


@router.post("/validate-coupon")
async def validate_coupon(body: ValidateCouponRequest, db: AsyncSession = Depends(get_db)):
    """Validate a coupon code at POS before applying it to a sale."""
    now = datetime.now(timezone.utc)

    result = await db.execute(select(Coupon).where(Coupon.code == body.code, Coupon.is_active == True))
    coupon = result.scalar_one_or_none()
    if not coupon:
        return {"valid": False, "error": "Coupon not found or inactive"}

    def _aware(dt):
        if dt is None:
            return None
        return dt if dt.tzinfo else dt.replace(tzinfo=timezone.utc)

    if _aware(coupon.valid_from) and _aware(coupon.valid_from) > now:
        return {"valid": False, "error": "Coupon not yet active"}
    if _aware(coupon.valid_until) and _aware(coupon.valid_until) < now:
        return {"valid": False, "error": "Coupon expired"}
    if coupon.max_uses is not None and coupon.used_count >= coupon.max_uses:
        return {"valid": False, "error": "Coupon usage limit reached"}
    if coupon.min_purchase and body.sale_total < coupon.min_purchase:
        return {"valid": False, "error": f"Minimum purchase €{coupon.min_purchase} required"}

    if body.customer_id:
        used_result = await db.execute(
            select(func.count()).select_from(CouponRedemption).where(
                CouponRedemption.coupon_id == coupon.id,
                CouponRedemption.customer_id == body.customer_id,
            )
        )
        customer_uses = used_result.scalar() or 0
        if customer_uses >= coupon.per_customer_limit:
            return {"valid": False, "error": "You have already used this coupon"}

    # compute discount amount
    if coupon.discount_type == "pct_discount":
        discount_amount = (body.sale_total * coupon.discount_value / 100).quantize(Decimal("0.01"))
    elif coupon.discount_type == "fixed_discount":
        discount_amount = min(coupon.discount_value, body.sale_total)
    else:
        discount_amount = Decimal("0")

    return {
        "valid": True,
        "coupon_id": str(coupon.id),
        "code": coupon.code,
        "name": coupon.name,
        "discount_type": coupon.discount_type,
        "discount_value": str(coupon.discount_value),
        "discount_amount": str(discount_amount),
        "error": None,
    }
