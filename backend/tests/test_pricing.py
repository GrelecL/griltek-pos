"""Tests for pricing rules and price computation."""
import uuid
from datetime import datetime, timedelta, timezone
from decimal import Decimal

import pytest

from app.models.catalog import Price, Product
from app.models.location import Location, LocationConfig
from app.models.pricing import PricingRule
from app.models.tenant import Tenant
from app.services.pricing import compute_price, get_base_price


async def _setup(db):
    tenant = Tenant(id=uuid.uuid4(), name="T", slug="t-pricing")
    db.add(tenant)
    await db.flush()
    loc = Location(id=uuid.uuid4(), tenant_id=tenant.id, name="L", address="A",
                   business_type="retail", timezone="UTC")
    db.add(loc)
    await db.flush()
    db.add(LocationConfig(id=uuid.uuid4(), location_id=loc.id))
    product = Product(
        id=uuid.uuid4(), tenant_id=tenant.id,
        plu="TEST-01", name="Test Beer",
        vat_rate=Decimal("9.5"), unit="piece",
        is_weighable=False, age_restricted=False, allergens=[], is_active=True,
    )
    db.add(product)
    await db.flush()
    return tenant, loc, product


async def _add_price(db, product_id, amount, location_id=None, min_qty=1):
    price = Price(
        id=uuid.uuid4(), product_id=product_id,
        location_id=location_id, price_type="regular",
        amount=Decimal(str(amount)), min_qty=min_qty, is_active=True,
    )
    db.add(price)
    await db.flush()
    return price


async def _add_rule(db, tenant_id, rule_type, action, conditions=None,
                    priority=100, stackable=True, valid_from=None, valid_until=None):
    rule = PricingRule(
        id=uuid.uuid4(), tenant_id=tenant_id,
        name=f"Rule {rule_type}", rule_type=rule_type,
        priority=priority, conditions=conditions or {},
        action=action, is_active=True, stackable=stackable,
        valid_from=valid_from, valid_until=valid_until,
    )
    db.add(rule)
    await db.flush()
    return rule


# ── get_base_price ────────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_base_price_returns_global(db):
    tenant, loc, product = await _setup(db)
    await _add_price(db, product.id, "2.99")
    await db.commit()
    price = await get_base_price(db, product.id, Decimal("1"))
    assert price == Decimal("2.99")


@pytest.mark.asyncio
async def test_base_price_location_overrides_global(db):
    tenant, loc, product = await _setup(db)
    await _add_price(db, product.id, "2.99")
    await _add_price(db, product.id, "2.50", location_id=loc.id)
    await db.commit()
    price = await get_base_price(db, product.id, Decimal("1"), location_id=loc.id)
    assert price == Decimal("2.50")


@pytest.mark.asyncio
async def test_base_price_volume_tier(db):
    tenant, loc, product = await _setup(db)
    await _add_price(db, product.id, "2.99", min_qty=1)
    await _add_price(db, product.id, "2.50", min_qty=6)  # 6-pack price
    await db.commit()
    single = await get_base_price(db, product.id, Decimal("1"))
    bulk = await get_base_price(db, product.id, Decimal("6"))
    assert single == Decimal("2.99")
    assert bulk == Decimal("2.50")


@pytest.mark.asyncio
async def test_base_price_expired_ignored(db):
    tenant, loc, product = await _setup(db)
    past = datetime.now(timezone.utc) - timedelta(days=1)
    await _add_price(db, product.id, "2.99")
    expired = Price(
        id=uuid.uuid4(), product_id=product.id, price_type="regular",
        amount=Decimal("1.00"), min_qty=1, is_active=True,
        valid_from=past - timedelta(days=10), valid_until=past,
    )
    db.add(expired)
    await db.commit()
    price = await get_base_price(db, product.id, Decimal("1"))
    assert price == Decimal("2.99")


@pytest.mark.asyncio
async def test_base_price_none_when_no_price(db):
    tenant, loc, product = await _setup(db)
    await db.commit()
    price = await get_base_price(db, product.id, Decimal("1"))
    assert price is None


# ── compute_price rules ───────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_pct_discount(db):
    tenant, loc, product = await _setup(db)
    await _add_rule(db, tenant.id, "pct_discount", {"value": 10})
    await db.commit()
    result = await compute_price(db, product.id, Decimal("10.00"), Decimal("1"), tenant.id)
    assert result.final_price == Decimal("9.00")
    assert result.discount_amount == Decimal("1.00")
    assert len(result.applied_rules) == 1


@pytest.mark.asyncio
async def test_fixed_discount(db):
    tenant, loc, product = await _setup(db)
    await _add_rule(db, tenant.id, "fixed_discount", {"value": "1.50"})
    await db.commit()
    result = await compute_price(db, product.id, Decimal("5.00"), Decimal("1"), tenant.id)
    assert result.final_price == Decimal("3.50")


@pytest.mark.asyncio
async def test_fixed_price(db):
    tenant, loc, product = await _setup(db)
    await _add_rule(db, tenant.id, "fixed_price", {"value": "1.99"})
    await db.commit()
    result = await compute_price(db, product.id, Decimal("5.00"), Decimal("1"), tenant.id)
    assert result.final_price == Decimal("1.99")


@pytest.mark.asyncio
async def test_bxgy_free_qty(db):
    tenant, loc, product = await _setup(db)
    # buy 2, get 1 free
    await _add_rule(db, tenant.id, "bxgy",
                    {"free_qty": 1}, conditions={"min_qty": 2})
    await db.commit()
    # qty=3: 1 set of (buy 2 + 1 free) → 1 free item
    result = await compute_price(db, product.id, Decimal("2.00"), Decimal("3"), tenant.id)
    assert result.free_qty == 1
    assert result.final_price == Decimal("2.00")  # price per unit unchanged


@pytest.mark.asyncio
async def test_rules_apply_in_priority_order(db):
    tenant, loc, product = await _setup(db)
    # priority 50 applies first (lower = higher priority)
    await _add_rule(db, tenant.id, "pct_discount", {"value": 10}, priority=50)
    await _add_rule(db, tenant.id, "fixed_discount", {"value": "0.50"}, priority=100)
    await db.commit()
    # 10.00 → 10% off = 9.00 → -0.50 = 8.50
    result = await compute_price(db, product.id, Decimal("10.00"), Decimal("1"), tenant.id)
    assert result.final_price == Decimal("8.50")


@pytest.mark.asyncio
async def test_non_stackable_stops_chain(db):
    tenant, loc, product = await _setup(db)
    await _add_rule(db, tenant.id, "pct_discount", {"value": 20}, priority=10, stackable=False)
    await _add_rule(db, tenant.id, "fixed_discount", {"value": "5.00"}, priority=20)
    await db.commit()
    # Only first (non-stackable) rule applied: 10.00 → 8.00
    result = await compute_price(db, product.id, Decimal("10.00"), Decimal("1"), tenant.id)
    assert result.final_price == Decimal("8.00")
    assert len(result.applied_rules) == 1


@pytest.mark.asyncio
async def test_rule_product_filter(db):
    tenant, loc, product = await _setup(db)
    other_id = uuid.uuid4()
    await _add_rule(db, tenant.id, "pct_discount", {"value": 50},
                    conditions={"product_ids": [str(other_id)]})
    await db.commit()
    # Rule targets a different product → not applied
    result = await compute_price(db, product.id, Decimal("10.00"), Decimal("1"), tenant.id)
    assert result.final_price == Decimal("10.00")
    assert result.applied_rules == []


@pytest.mark.asyncio
async def test_rule_customer_tier_filter(db):
    tenant, loc, product = await _setup(db)
    await _add_rule(db, tenant.id, "pct_discount", {"value": 15},
                    conditions={"customer_tiers": ["gold"]})
    await db.commit()
    # No tier → not applied
    result_no_tier = await compute_price(db, product.id, Decimal("10.00"), Decimal("1"), tenant.id)
    assert result_no_tier.applied_rules == []
    # Gold tier → applied
    result_gold = await compute_price(db, product.id, Decimal("10.00"), Decimal("1"),
                                      tenant.id, customer_tier="gold")
    assert result_gold.final_price == Decimal("8.50")


@pytest.mark.asyncio
async def test_rule_expired_not_applied(db):
    tenant, loc, product = await _setup(db)
    past = datetime.now(timezone.utc) - timedelta(days=1)
    await _add_rule(db, tenant.id, "pct_discount", {"value": 50},
                    valid_until=past)
    await db.commit()
    result = await compute_price(db, product.id, Decimal("10.00"), Decimal("1"), tenant.id)
    assert result.final_price == Decimal("10.00")


@pytest.mark.asyncio
async def test_fixed_discount_cannot_go_below_zero(db):
    tenant, loc, product = await _setup(db)
    await _add_rule(db, tenant.id, "fixed_discount", {"value": "999"})
    await db.commit()
    result = await compute_price(db, product.id, Decimal("5.00"), Decimal("1"), tenant.id)
    assert result.final_price == Decimal("0.00")
