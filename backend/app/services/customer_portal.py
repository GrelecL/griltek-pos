"""Customer portal service: auth, loyalty, coupons, receipts."""
from __future__ import annotations

import hashlib
import uuid
from datetime import datetime, timedelta, timezone
from decimal import Decimal

from jose import JWTError, jwt
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.core.config import settings
from app.models.coupon import Coupon, CouponRedemption
from app.models.customer import Customer
from app.models.payments import LoyaltyAccount, LoyaltyProgram
from app.models.portal import CustomerPortalAccount
from app.models.pos import Payment, Sale, SaleLine
from app.models.tenant import Tenant


def _hash_pin(pin: str) -> str:
    return hashlib.sha256(pin.encode()).hexdigest()


def _create_customer_token(customer_id: uuid.UUID, tenant_id: uuid.UUID) -> str:
    payload = {
        "sub": str(customer_id),
        "tenant_id": str(tenant_id),
        "type": "customer",
        "exp": datetime.now(timezone.utc) + timedelta(days=30),
    }
    return jwt.encode(payload, settings.secret_key, algorithm="HS256")


def decode_customer_token(token: str) -> dict:
    payload = jwt.decode(token, settings.secret_key, algorithms=["HS256"])
    if payload.get("type") != "customer":
        raise JWTError("not a customer token")
    return payload


async def _get_tenant(db: AsyncSession, slug: str) -> Tenant | None:
    result = await db.execute(select(Tenant).where(Tenant.slug == slug))
    return result.scalar_one_or_none()


async def register(
    db: AsyncSession,
    tenant_slug: str,
    phone: str | None,
    email: str | None,
    pin: str,
) -> tuple[str, Customer]:
    """Create portal account for an existing customer matched by phone or email."""
    tenant = await _get_tenant(db, tenant_slug)
    if not tenant:
        raise ValueError("Tenant not found")

    q = select(Customer).where(Customer.tenant_id == tenant.id)
    if phone:
        q = q.where(Customer.phone == phone)
    elif email:
        q = q.where(Customer.email == email)
    else:
        raise ValueError("Provide phone or email")

    result = await db.execute(q)
    customer = result.scalar_one_or_none()
    if not customer:
        raise ValueError("No customer found with that contact")

    # check if account already exists
    existing = await db.execute(
        select(CustomerPortalAccount).where(CustomerPortalAccount.customer_id == customer.id)
    )
    account = existing.scalar_one_or_none()
    if account:
        raise ValueError("Portal account already registered — use login")

    account = CustomerPortalAccount(
        id=uuid.uuid4(),
        customer_id=customer.id,
        pin_hash=_hash_pin(pin),
    )
    db.add(account)
    await db.flush()
    token = _create_customer_token(customer.id, tenant.id)
    return token, customer


async def login(
    db: AsyncSession,
    tenant_slug: str,
    phone: str | None,
    email: str | None,
    pin: str,
) -> tuple[str, Customer]:
    tenant = await _get_tenant(db, tenant_slug)
    if not tenant:
        raise ValueError("Tenant not found")

    q = select(Customer).where(Customer.tenant_id == tenant.id)
    if phone:
        q = q.where(Customer.phone == phone)
    elif email:
        q = q.where(Customer.email == email)
    else:
        raise ValueError("Provide phone or email")

    result = await db.execute(q)
    customer = result.scalar_one_or_none()
    if not customer:
        raise ValueError("Invalid credentials")

    account_result = await db.execute(
        select(CustomerPortalAccount).where(CustomerPortalAccount.customer_id == customer.id)
    )
    account = account_result.scalar_one_or_none()
    if not account or not account.is_active:
        raise ValueError("No portal account — please register first")
    if account.pin_hash != _hash_pin(pin):
        raise ValueError("Invalid credentials")

    token = _create_customer_token(customer.id, tenant.id)
    return token, customer


async def get_loyalty_summary(
    db: AsyncSession,
    customer_id: uuid.UUID,
    tenant_id: uuid.UUID,
) -> dict:
    program_result = await db.execute(
        select(LoyaltyProgram).where(
            LoyaltyProgram.tenant_id == tenant_id,
            LoyaltyProgram.is_active == True,
        )
    )
    program = program_result.scalar_one_or_none()
    if not program:
        return {"enrolled": False}

    account_result = await db.execute(
        select(LoyaltyAccount).where(
            LoyaltyAccount.program_id == program.id,
            LoyaltyAccount.customer_id == customer_id,
        )
    )
    account = account_result.scalar_one_or_none()
    if not account:
        return {"enrolled": False}

    # compute next tier threshold
    tiers = sorted(program.tiers or [], key=lambda t: t["min_points"])
    next_tier = None
    next_tier_points_needed = None
    for tier in tiers:
        if account.points_lifetime < tier["min_points"]:
            next_tier = tier["name"]
            next_tier_points_needed = tier["min_points"] - account.points_lifetime
            break

    redeem_value = (Decimal(str(account.points_balance)) * program.redeem_rate).quantize(Decimal("0.01"))

    return {
        "enrolled": True,
        "program_name": program.name,
        "points_balance": account.points_balance,
        "points_lifetime": account.points_lifetime,
        "tier": account.tier,
        "redeem_value": str(redeem_value),
        "next_tier": next_tier,
        "next_tier_points_needed": next_tier_points_needed,
        "tiers": tiers,
    }


async def get_receipts(
    db: AsyncSession,
    customer_id: uuid.UUID,
    limit: int = 20,
    offset: int = 0,
) -> list[dict]:
    result = await db.execute(
        select(Sale)
        .where(Sale.customer_id == customer_id, Sale.status == "completed")
        .options(selectinload(Sale.lines), selectinload(Sale.payments))
        .order_by(Sale.completed_at.desc())
        .limit(limit)
        .offset(offset)
    )
    sales = result.scalars().all()
    return [_sale_to_receipt(s) for s in sales]


async def get_receipt(db: AsyncSession, customer_id: uuid.UUID, sale_id: uuid.UUID) -> dict | None:
    result = await db.execute(
        select(Sale)
        .where(Sale.id == sale_id, Sale.customer_id == customer_id)
        .options(selectinload(Sale.lines), selectinload(Sale.payments))
    )
    sale = result.scalar_one_or_none()
    if not sale:
        return None
    return _sale_to_receipt(sale)


def _sale_to_receipt(sale: Sale) -> dict:
    return {
        "id": str(sale.id),
        "completed_at": sale.completed_at.isoformat(),
        "total": str(sale.total),
        "subtotal": str(sale.subtotal),
        "vat_total": str(sale.vat_total),
        "discount_total": str(sale.discount_total),
        "sale_type": sale.sale_type,
        "lines": [
            {
                "product_name": l.product_name,
                "plu": l.plu,
                "qty": str(l.qty),
                "unit_price": str(l.unit_price),
                "line_total": str(l.line_total),
                "vat_rate": str(l.vat_rate),
            }
            for l in sale.lines
        ],
        "payments": [
            {"method": p.method, "amount": str(p.amount)}
            for p in sale.payments
        ],
    }


async def get_available_coupons(
    db: AsyncSession,
    customer_id: uuid.UUID,
    tenant_id: uuid.UUID,
) -> list[dict]:
    now = datetime.now(timezone.utc)

    result = await db.execute(
        select(Coupon).where(
            Coupon.tenant_id == tenant_id,
            Coupon.is_active == True,
        )
    )
    all_coupons = result.scalars().all()

    # filter valid date range and usage limits
    valid = []
    for c in all_coupons:
        def _aware(dt):
            if dt is None:
                return None
            return dt if dt.tzinfo else dt.replace(tzinfo=timezone.utc)

        if _aware(c.valid_from) and _aware(c.valid_from) > now:
            continue
        if _aware(c.valid_until) and _aware(c.valid_until) < now:
            continue
        if c.max_uses is not None and c.used_count >= c.max_uses:
            continue
        valid.append(c)

    if not valid:
        return []

    # check per-customer usage
    coupon_ids = [c.id for c in valid]
    redemptions_result = await db.execute(
        select(CouponRedemption.coupon_id, func.count().label("cnt"))
        .where(
            CouponRedemption.customer_id == customer_id,
            CouponRedemption.coupon_id.in_(coupon_ids),
        )
        .group_by(CouponRedemption.coupon_id)
    )
    used_counts = {str(row.coupon_id): row.cnt for row in redemptions_result}

    output = []
    for c in valid:
        customer_uses = used_counts.get(str(c.id), 0)
        if customer_uses >= c.per_customer_limit:
            continue
        output.append({
            "id": str(c.id),
            "code": c.code,
            "name": c.name,
            "description": c.description,
            "discount_type": c.discount_type,
            "discount_value": str(c.discount_value),
            "min_purchase": str(c.min_purchase) if c.min_purchase else None,
            "valid_until": _aware(c.valid_until).isoformat() if _aware(c.valid_until) else None,
            "uses_remaining": c.per_customer_limit - customer_uses,
        })
    return output
