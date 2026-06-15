"""Tests for customer portal: auth, loyalty, coupons, receipts."""
import uuid
from datetime import datetime, timedelta, timezone
from decimal import Decimal

import pytest
from sqlalchemy import select

from app.models.auth import Role, User
from app.models.coupon import Coupon, CouponRedemption
from app.models.customer import Customer
from app.models.location import Location, LocationConfig
from app.models.payments import LoyaltyAccount, LoyaltyProgram
from app.models.portal import CustomerPortalAccount
from app.models.pos import CashSession, Payment, Sale, SaleLine
from app.models.tenant import Tenant
from app.services import customer_portal as portal_svc


async def _make_tenant(db, slug="t-portal"):
    t = Tenant(id=uuid.uuid4(), name="T", slug=slug)
    db.add(t)
    await db.flush()
    return t


async def _make_customer(db, tenant_id, phone="+38641000001", email="test@test.si"):
    c = Customer(id=uuid.uuid4(), tenant_id=tenant_id, name="Ana Novak",
                 phone=phone, email=email)
    db.add(c)
    await db.flush()
    return c


async def _make_sale(db, customer_id, total=Decimal("20.00")):
    tenant = Tenant(id=uuid.uuid4(), name="T2", slug=f"t-{uuid.uuid4().hex[:4]}")
    db.add(tenant)
    await db.flush()
    loc = Location(id=uuid.uuid4(), tenant_id=tenant.id, name="L", address="A",
                   business_type="retail", timezone="UTC")
    db.add(loc)
    await db.flush()
    db.add(LocationConfig(id=uuid.uuid4(), location_id=loc.id))
    role = Role(id=uuid.uuid4(), tenant_id=tenant.id, name="r", permissions=[])
    db.add(role)
    await db.flush()
    user = User(id=uuid.uuid4(), tenant_id=tenant.id, role_id=role.id,
                username=f"u-{uuid.uuid4().hex[:4]}", display_name="U", pin_hash="x")
    db.add(user)
    await db.flush()
    session = CashSession(id=uuid.uuid4(), location_id=loc.id, user_id=user.id,
                          status="open", opening_float=Decimal("0"))
    db.add(session)
    await db.flush()
    sale = Sale(
        id=uuid.uuid4(), transaction_uuid=uuid.uuid4(),
        cash_session_id=session.id, location_id=loc.id, user_id=user.id,
        customer_id=customer_id, sale_type="sale", status="completed",
        subtotal=total, discount_total=Decimal("0"),
        vat_total=Decimal("0"), total=total,
    )
    db.add(sale)
    await db.flush()
    db.add(SaleLine(
        id=uuid.uuid4(), sale_id=sale.id, product_id=uuid.uuid4(),
        product_name="Pivo", plu="500", qty=Decimal("2"),
        unit_price=Decimal("2.50"), vat_rate=Decimal("9.5"),
        line_total=total, vat_amount=Decimal("0"),
        discount_pct=Decimal("0"), discount_amount=Decimal("0"),
    ))
    db.add(Payment(id=uuid.uuid4(), sale_id=sale.id, method="cash",
                   amount=total, status="completed"))
    return sale


# ── register & login ──────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_register_creates_account(db):
    tenant = await _make_tenant(db)
    await _make_customer(db, tenant.id, phone="+38641001001")
    await db.commit()

    token, customer = await portal_svc.register(db, tenant.slug, "+38641001001", None, "1234")
    await db.commit()

    assert token != ""
    payload = portal_svc.decode_customer_token(token)
    assert payload["type"] == "customer"
    assert payload["tenant_id"] == str(tenant.id)


@pytest.mark.asyncio
async def test_register_duplicate_raises(db):
    tenant = await _make_tenant(db, "t-dup")
    await _make_customer(db, tenant.id, phone="+38641002002")
    await db.commit()
    await portal_svc.register(db, tenant.slug, "+38641002002", None, "1234")
    await db.commit()
    with pytest.raises(ValueError, match="already registered"):
        await portal_svc.register(db, tenant.slug, "+38641002002", None, "9999")


@pytest.mark.asyncio
async def test_login_success(db):
    tenant = await _make_tenant(db, "t-login")
    await _make_customer(db, tenant.id, phone="+38641003003")
    await db.commit()
    await portal_svc.register(db, tenant.slug, "+38641003003", None, "5678")
    await db.commit()

    token, _ = await portal_svc.login(db, tenant.slug, "+38641003003", None, "5678")
    assert token != ""


@pytest.mark.asyncio
async def test_login_wrong_pin_raises(db):
    tenant = await _make_tenant(db, "t-wrongpin")
    await _make_customer(db, tenant.id, phone="+38641004004")
    await db.commit()
    await portal_svc.register(db, tenant.slug, "+38641004004", None, "1111")
    await db.commit()
    with pytest.raises(ValueError, match="Invalid credentials"):
        await portal_svc.login(db, tenant.slug, "+38641004004", None, "9999")


@pytest.mark.asyncio
async def test_login_by_email(db):
    tenant = await _make_tenant(db, "t-email")
    await _make_customer(db, tenant.id, phone="+38641005005", email="login@test.si")
    await db.commit()
    await portal_svc.register(db, tenant.slug, None, "login@test.si", "4321")
    await db.commit()
    token, _ = await portal_svc.login(db, tenant.slug, None, "login@test.si", "4321")
    assert token != ""


# ── loyalty ───────────────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_loyalty_summary_not_enrolled(db):
    tenant = await _make_tenant(db, "t-noprogram")
    customer = await _make_customer(db, tenant.id)
    await db.commit()
    summary = await portal_svc.get_loyalty_summary(db, customer.id, tenant.id)
    assert summary["enrolled"] is False


@pytest.mark.asyncio
async def test_loyalty_summary_with_points(db):
    tenant = await _make_tenant(db, "t-loyalty")
    customer = await _make_customer(db, tenant.id)
    prog = LoyaltyProgram(
        id=uuid.uuid4(), tenant_id=tenant.id, name="Zvestoba",
        earn_rate=Decimal("1"), redeem_rate=Decimal("0.01"),
        min_redeem_points=100, is_active=True,
        tiers=[
            {"name": "standard", "min_points": 0, "earn_multiplier": 1},
            {"name": "silver", "min_points": 500, "earn_multiplier": 1.5},
        ],
    )
    db.add(prog)
    await db.flush()
    db.add(LoyaltyAccount(
        id=uuid.uuid4(), program_id=prog.id, customer_id=customer.id,
        points_balance=250, points_lifetime=250, tier="standard",
    ))
    await db.commit()

    summary = await portal_svc.get_loyalty_summary(db, customer.id, tenant.id)
    assert summary["enrolled"] is True
    assert summary["points_balance"] == 250
    assert summary["tier"] == "standard"
    assert summary["next_tier"] == "silver"
    assert summary["next_tier_points_needed"] == 250


# ── receipts ──────────────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_get_receipts(db):
    tenant = await _make_tenant(db, "t-receipts")
    customer = await _make_customer(db, tenant.id)
    await _make_sale(db, customer.id, Decimal("15.00"))
    await _make_sale(db, customer.id, Decimal("30.00"))
    await db.commit()

    receipts = await portal_svc.get_receipts(db, customer.id)
    assert len(receipts) == 2
    totals = {r["total"] for r in receipts}
    assert "15.00" in totals
    assert "30.00" in totals


@pytest.mark.asyncio
async def test_get_receipt_has_lines_and_payments(db):
    tenant = await _make_tenant(db, "t-receipt-detail")
    customer = await _make_customer(db, tenant.id)
    sale = await _make_sale(db, customer.id, Decimal("10.00"))
    await db.commit()

    receipt = await portal_svc.get_receipt(db, customer.id, sale.id)
    assert receipt is not None
    assert len(receipt["lines"]) == 1
    assert len(receipt["payments"]) == 1
    assert receipt["lines"][0]["product_name"] == "Pivo"
    assert receipt["payments"][0]["method"] == "cash"


@pytest.mark.asyncio
async def test_get_receipt_wrong_customer_returns_none(db):
    tenant = await _make_tenant(db, "t-receipt-other")
    customer = await _make_customer(db, tenant.id)
    sale = await _make_sale(db, customer.id)
    await db.commit()

    other_id = uuid.uuid4()
    receipt = await portal_svc.get_receipt(db, other_id, sale.id)
    assert receipt is None


# ── coupons ───────────────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_get_available_coupons(db):
    tenant = await _make_tenant(db, "t-coupons")
    customer = await _make_customer(db, tenant.id)
    db.add(Coupon(
        id=uuid.uuid4(), tenant_id=tenant.id,
        code="SAVE10", name="10% OFF", discount_type="pct_discount",
        discount_value=Decimal("10"), per_customer_limit=1,
        used_count=0, is_active=True,
    ))
    await db.commit()

    coupons = await portal_svc.get_available_coupons(db, customer.id, tenant.id)
    assert len(coupons) == 1
    assert coupons[0]["code"] == "SAVE10"


@pytest.mark.asyncio
async def test_expired_coupon_hidden(db):
    tenant = await _make_tenant(db, "t-expired")
    customer = await _make_customer(db, tenant.id)
    past = datetime.now(timezone.utc) - timedelta(days=1)
    db.add(Coupon(
        id=uuid.uuid4(), tenant_id=tenant.id,
        code="OLDCODE", name="Expired", discount_type="pct_discount",
        discount_value=Decimal("5"), per_customer_limit=1,
        used_count=0, is_active=True, valid_until=past,
    ))
    await db.commit()

    coupons = await portal_svc.get_available_coupons(db, customer.id, tenant.id)
    assert len(coupons) == 0


@pytest.mark.asyncio
async def test_used_coupon_hidden(db):
    tenant = await _make_tenant(db, "t-usedcoup")
    customer = await _make_customer(db, tenant.id)
    coupon = Coupon(
        id=uuid.uuid4(), tenant_id=tenant.id,
        code="USED1", name="Used", discount_type="fixed_discount",
        discount_value=Decimal("2"), per_customer_limit=1,
        used_count=0, is_active=True,
    )
    db.add(coupon)
    await db.flush()
    db.add(CouponRedemption(
        id=uuid.uuid4(), coupon_id=coupon.id, customer_id=customer.id,
        redeemed_at=datetime.now(timezone.utc),
    ))
    await db.commit()

    coupons = await portal_svc.get_available_coupons(db, customer.id, tenant.id)
    assert len(coupons) == 0
