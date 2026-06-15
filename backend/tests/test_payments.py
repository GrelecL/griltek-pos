"""Tests for gift cards, loyalty, credit, SumUp adapter, split payment."""
import uuid
from datetime import datetime, timedelta, timezone
from decimal import Decimal

import pytest

from app.adapters.sumup.adapter import MockSumUpAdapter, SumUpChargeRequest
from app.models.customer import CreditAccount, Customer
from app.models.payments import (
    LoyaltyProgram,
)
from app.models.pos import CashSession, Sale
from app.models.tenant import Tenant
from app.services import credit as credit_svc
from app.services import gift_card as gc_svc
from app.services import loyalty as loyalty_svc
from app.services.split_payment import process_split_payments

# ── fixtures ──────────────────────────────────────────────────────────────────

async def _make_tenant(db) -> Tenant:
    t = Tenant(id=uuid.uuid4(), name="T", slug="t")
    db.add(t)
    await db.flush()
    return t


async def _make_customer(db, tenant_id) -> Customer:
    c = Customer(id=uuid.uuid4(), tenant_id=tenant_id, name="Ana Novak")
    db.add(c)
    await db.flush()
    return c


async def _make_sale(db, tenant_id, total: Decimal = Decimal("10.00")) -> Sale:
    from app.models.auth import Role, User
    from app.models.location import Location, LocationConfig
    loc = Location(id=uuid.uuid4(), tenant_id=tenant_id, name="L", address="A", business_type="retail", timezone="UTC")
    db.add(loc)
    await db.flush()
    cfg = LocationConfig(id=uuid.uuid4(), location_id=loc.id)
    db.add(cfg)
    role = Role(id=uuid.uuid4(), tenant_id=tenant_id, name="r", permissions=[])
    db.add(role)
    await db.flush()
    user = User(id=uuid.uuid4(), tenant_id=tenant_id, role_id=role.id, username="u", display_name="U", pin_hash="x")
    db.add(user)
    await db.flush()
    session = CashSession(id=uuid.uuid4(), location_id=loc.id, user_id=user.id, status="open", opening_float=Decimal("0"))
    db.add(session)
    await db.flush()
    sale = Sale(
        id=uuid.uuid4(), transaction_uuid=uuid.uuid4(),
        cash_session_id=session.id, location_id=loc.id,
        user_id=user.id, sale_type="sale", status="completed",
        subtotal=total, discount_total=Decimal("0"),
        vat_total=Decimal("0"), total=total,
    )
    db.add(sale)
    await db.flush()
    return sale


# ── gift card ─────────────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_issue_gift_card(db):
    tenant = await _make_tenant(db)
    card = await gc_svc.issue(db, tenant.id, Decimal("50.00"))
    await db.commit()
    assert card.balance == Decimal("50.00")
    assert card.status == "active"
    assert len(card.code) > 0


@pytest.mark.asyncio
async def test_gift_card_redeem(db):
    tenant = await _make_tenant(db)
    card = await gc_svc.issue(db, tenant.id, Decimal("20.00"))
    await db.flush()
    actual = await gc_svc.redeem(db, card, Decimal("15.00"))
    await db.commit()
    assert actual == Decimal("15.00")
    assert card.balance == Decimal("5.00")
    assert card.status == "active"


@pytest.mark.asyncio
async def test_gift_card_redeem_partial_and_zero(db):
    tenant = await _make_tenant(db)
    card = await gc_svc.issue(db, tenant.id, Decimal("10.00"))
    await db.flush()
    # Redeem more than balance → only redeems available amount
    actual = await gc_svc.redeem(db, card, Decimal("15.00"))
    await db.commit()
    assert actual == Decimal("10.00")
    assert card.balance == Decimal("0")
    assert card.status == "redeemed"


@pytest.mark.asyncio
async def test_gift_card_expired_rejected(db):
    tenant = await _make_tenant(db)
    past = datetime.now(timezone.utc) - timedelta(days=1)
    card = await gc_svc.issue(db, tenant.id, Decimal("10.00"), valid_until=past)
    await db.flush()
    err = await gc_svc.validate(card)
    assert err is not None
    assert "expired" in err.lower()


@pytest.mark.asyncio
async def test_gift_card_topup(db):
    tenant = await _make_tenant(db)
    card = await gc_svc.issue(db, tenant.id, Decimal("10.00"))
    await db.flush()
    await gc_svc.topup(db, card, Decimal("5.00"))
    await db.commit()
    assert card.balance == Decimal("15.00")


@pytest.mark.asyncio
async def test_gift_card_generate_code_unique(db):
    code1 = gc_svc.generate_code()
    code2 = gc_svc.generate_code()
    assert code1 != code2
    assert len(code1) == 19  # XXXX-XXXX-XXXX-XXXX


# ── loyalty ───────────────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_loyalty_earn_points(db):
    tenant = await _make_tenant(db)
    customer = await _make_customer(db, tenant.id)
    prog = LoyaltyProgram(
        id=uuid.uuid4(), tenant_id=tenant.id, name="Zvestoba",
        earn_rate=Decimal("1.0"), redeem_rate=Decimal("0.01"),
        min_redeem_points=100, tiers=[],
    )
    db.add(prog)
    await db.flush()
    account = await loyalty_svc.get_or_create_account(db, prog.id, customer.id)
    earned = await loyalty_svc.earn_points(db, prog, account, Decimal("25.50"))
    await db.commit()
    assert earned == 25
    assert account.points_balance == 25
    assert account.points_lifetime == 25


@pytest.mark.asyncio
async def test_loyalty_redeem_points(db):
    tenant = await _make_tenant(db)
    customer = await _make_customer(db, tenant.id)
    prog = LoyaltyProgram(
        id=uuid.uuid4(), tenant_id=tenant.id, name="Z",
        earn_rate=Decimal("1.0"), redeem_rate=Decimal("0.01"),
        min_redeem_points=100, tiers=[],
    )
    db.add(prog)
    await db.flush()
    account = await loyalty_svc.get_or_create_account(db, prog.id, customer.id)
    await loyalty_svc.earn_points(db, prog, account, Decimal("500.00"))
    euro = await loyalty_svc.redeem_points(db, prog, account, 200)
    await db.commit()
    assert euro == Decimal("2.00")
    assert account.points_balance == 300


@pytest.mark.asyncio
async def test_loyalty_redeem_below_minimum_fails(db):
    tenant = await _make_tenant(db)
    customer = await _make_customer(db, tenant.id)
    prog = LoyaltyProgram(
        id=uuid.uuid4(), tenant_id=tenant.id, name="Z",
        earn_rate=Decimal("1.0"), redeem_rate=Decimal("0.01"),
        min_redeem_points=100, tiers=[],
    )
    db.add(prog)
    await db.flush()
    account = await loyalty_svc.get_or_create_account(db, prog.id, customer.id)
    await loyalty_svc.earn_points(db, prog, account, Decimal("200.00"))
    with pytest.raises(ValueError, match="Minimum"):
        await loyalty_svc.redeem_points(db, prog, account, 50)


@pytest.mark.asyncio
async def test_loyalty_tier_upgrade(db):
    tenant = await _make_tenant(db)
    customer = await _make_customer(db, tenant.id)
    tiers = [
        {"name": "standard", "min_points": 0, "earn_multiplier": 1},
        {"name": "silver", "min_points": 500, "earn_multiplier": 1.5},
        {"name": "gold", "min_points": 1000, "earn_multiplier": 2},
    ]
    prog = LoyaltyProgram(
        id=uuid.uuid4(), tenant_id=tenant.id, name="Z",
        earn_rate=Decimal("1.0"), redeem_rate=Decimal("0.01"),
        min_redeem_points=100, tiers=tiers,
    )
    db.add(prog)
    await db.flush()
    account = await loyalty_svc.get_or_create_account(db, prog.id, customer.id)
    await loyalty_svc.earn_points(db, prog, account, Decimal("600.00"))
    await db.commit()
    assert account.tier == "silver"


# ── credit ────────────────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_credit_charge_and_settle(db):
    tenant = await _make_tenant(db)
    customer = await _make_customer(db, tenant.id)
    account = CreditAccount(
        id=uuid.uuid4(), customer_id=customer.id,
        credit_limit=Decimal("500.00"), balance=Decimal("0"), is_active=True,
    )
    db.add(account)
    await db.flush()

    await credit_svc.charge(db, account, Decimal("120.00"), note="Purchase")
    await db.commit()
    assert account.balance == Decimal("120.00")

    await credit_svc.settle(db, account, Decimal("50.00"))
    await db.commit()
    assert account.balance == Decimal("70.00")


@pytest.mark.asyncio
async def test_credit_limit_exceeded_raises(db):
    tenant = await _make_tenant(db)
    customer = await _make_customer(db, tenant.id)
    account = CreditAccount(
        id=uuid.uuid4(), customer_id=customer.id,
        credit_limit=Decimal("100.00"), balance=Decimal("0"), is_active=True,
    )
    db.add(account)
    await db.flush()
    with pytest.raises(ValueError, match="Credit limit"):
        await credit_svc.charge(db, account, Decimal("150.00"))


# ── SumUp adapter ─────────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_mock_sumup_approves():
    adapter = MockSumUpAdapter()
    resp = await adapter.charge(SumUpChargeRequest(amount="29.99"))
    assert resp.approved is True
    assert resp.transaction_id != ""
    assert resp.amount == "29.99"


# ── split payment ─────────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_split_cash_payment(db):
    tenant = await _make_tenant(db)
    sale = await _make_sale(db, tenant.id, Decimal("15.00"))
    payments = await process_split_payments(
        db, sale.id, sale.total,
        [{"method": "cash", "amount": "15.00", "cash_given": "20.00"}],
    )
    await db.commit()
    assert len(payments) == 1
    assert payments[0].method == "cash"
    assert payments[0].change_given == Decimal("5.00")


@pytest.mark.asyncio
async def test_split_sumup_payment(db):
    tenant = await _make_tenant(db)
    sale = await _make_sale(db, tenant.id, Decimal("25.00"))
    payments = await process_split_payments(
        db, sale.id, sale.total,
        [{"method": "sumup", "amount": "25.00"}],
    )
    await db.commit()
    assert len(payments) == 1
    assert payments[0].method == "sumup"
    assert payments[0].reference != ""


@pytest.mark.asyncio
async def test_split_gift_card_payment(db):
    tenant = await _make_tenant(db)
    card = await gc_svc.issue(db, tenant.id, Decimal("30.00"))
    await db.flush()
    sale = await _make_sale(db, tenant.id, Decimal("20.00"))
    payments = await process_split_payments(
        db, sale.id, sale.total,
        [{"method": "gift", "amount": "20.00", "reference": card.code}],
    )
    await db.commit()
    assert payments[0].method == "gift"
    assert payments[0].amount == Decimal("20.00")
    await db.refresh(card)
    assert card.balance == Decimal("10.00")


@pytest.mark.asyncio
async def test_split_multi_method(db):
    tenant = await _make_tenant(db)
    card = await gc_svc.issue(db, tenant.id, Decimal("5.00"))
    await db.flush()
    sale = await _make_sale(db, tenant.id, Decimal("15.00"))
    payments = await process_split_payments(
        db, sale.id, sale.total,
        [
            {"method": "gift", "amount": "5.00", "reference": card.code},
            {"method": "cash", "amount": "10.00", "cash_given": "10.00"},
        ],
    )
    await db.commit()
    assert len(payments) == 2
    total_paid = sum(p.amount for p in payments)
    assert total_paid == Decimal("15.00")


@pytest.mark.asyncio
async def test_split_underpaid_raises(db):
    tenant = await _make_tenant(db)
    sale = await _make_sale(db, tenant.id, Decimal("20.00"))
    with pytest.raises(ValueError, match="Underpaid"):
        await process_split_payments(
            db, sale.id, sale.total,
            [{"method": "cash", "amount": "10.00"}],
        )
