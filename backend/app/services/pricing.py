"""Pricing service: resolves base price and applies promotional rules."""
from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone
from decimal import Decimal

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.catalog import Price
from app.models.pricing import PricingRule


@dataclass
class PriceResult:
    base_price: Decimal
    final_price: Decimal
    discount_amount: Decimal
    applied_rules: list[str] = field(default_factory=list)
    free_qty: int = 0  # extra free units awarded by bxgy rules


async def get_base_price(
    db: AsyncSession,
    product_id: uuid.UUID,
    qty: Decimal,
    location_id: uuid.UUID | None = None,
    now: datetime | None = None,
) -> Decimal | None:
    """
    Resolve the effective base price from the Price table.

    Priority: location-specific > global; higher min_qty threshold > lower;
    most-recently-started validity window > older. Returns None if no price found.
    """
    if now is None:
        now = datetime.now(timezone.utc)

    result = await db.execute(
        select(Price)
        .where(
            Price.product_id == product_id,
            Price.is_active == True,
            Price.min_qty <= int(qty),
        )
        .order_by(
            # location-specific rows first (NULL last)
            Price.location_id.is_(None),
            # highest min_qty threshold first (volume pricing)
            Price.min_qty.desc(),
            # most recently activated price first
            Price.valid_from.desc().nulls_last(),
        )
    )
    prices = list(result.scalars().all())

    def _aware(dt):
        if dt is None:
            return None
        return dt if dt.tzinfo else dt.replace(tzinfo=timezone.utc)

    # filter by validity window
    valid = [
        p for p in prices
        if (_aware(p.valid_from) is None or _aware(p.valid_from) <= now)
        and (_aware(p.valid_until) is None or _aware(p.valid_until) >= now)
    ]

    if not valid:
        return None

    # prefer location-specific over global
    location_prices = [p for p in valid if p.location_id == location_id]
    return (location_prices or valid)[0].amount


async def get_active_rules(
    db: AsyncSession,
    tenant_id: uuid.UUID,
    now: datetime | None = None,
) -> list[PricingRule]:
    if now is None:
        now = datetime.now(timezone.utc)

    result = await db.execute(
        select(PricingRule)
        .where(PricingRule.tenant_id == tenant_id, PricingRule.is_active == True)
        .order_by(PricingRule.priority)
    )
    rules = list(result.scalars().all())
    def _aware(dt):
        if dt is None:
            return None
        return dt if dt.tzinfo else dt.replace(tzinfo=timezone.utc)

    return [
        r for r in rules
        if (_aware(r.valid_from) is None or _aware(r.valid_from) <= now)
        and (_aware(r.valid_until) is None or _aware(r.valid_until) >= now)
    ]


def _rule_matches(
    rule: PricingRule,
    product_id: uuid.UUID,
    category_id: uuid.UUID | None,
    qty: Decimal,
    customer_tier: str | None,
    now: datetime,
) -> bool:
    c = rule.conditions

    if c.get("product_ids") and str(product_id) not in c["product_ids"]:
        return False

    if c.get("category_ids") and str(category_id) not in c["category_ids"]:
        return False

    if c.get("min_qty") and qty < Decimal(str(c["min_qty"])):
        return False

    if c.get("customer_tiers") and customer_tier not in c["customer_tiers"]:
        return False

    if c.get("time_from") and c.get("time_to"):
        t = now.strftime("%H:%M")
        if not (c["time_from"] <= t <= c["time_to"]):
            return False

    if c.get("days_of_week") and now.weekday() not in c["days_of_week"]:
        return False

    return True


async def compute_price(
    db: AsyncSession,
    product_id: uuid.UUID,
    base_price: Decimal,
    qty: Decimal,
    tenant_id: uuid.UUID,
    category_id: uuid.UUID | None = None,
    customer_tier: str | None = None,
    now: datetime | None = None,
) -> PriceResult:
    """Apply active PricingRules in priority order to base_price."""
    if now is None:
        now = datetime.now(timezone.utc)

    rules = await get_active_rules(db, tenant_id, now)
    applicable = [
        r for r in rules
        if _rule_matches(r, product_id, category_id, qty, customer_tier, now)
    ]

    current_price = base_price
    applied: list[str] = []
    free_qty = 0

    for rule in applicable:
        a = rule.action

        if rule.rule_type == "pct_discount":
            pct = Decimal(str(a["value"]))
            current_price = (current_price * (1 - pct / 100)).quantize(Decimal("0.0001"))
            applied.append(rule.name)

        elif rule.rule_type == "fixed_discount":
            discount = Decimal(str(a["value"]))
            current_price = max(Decimal("0"), current_price - discount)
            applied.append(rule.name)

        elif rule.rule_type == "fixed_price":
            current_price = Decimal(str(a["value"]))
            applied.append(rule.name)

        elif rule.rule_type == "bxgy":
            # buy min_qty items, get free_qty items free
            buy_n = int(rule.conditions.get("min_qty", 1))
            get_n = int(a.get("free_qty", 1))
            sets = int(qty) // (buy_n + get_n)
            free_qty += sets * get_n
            applied.append(rule.name)

        if not rule.stackable:
            break

    final_price = current_price.quantize(Decimal("0.01"))
    discount_amount = max(Decimal("0"), (base_price - final_price).quantize(Decimal("0.01")))

    return PriceResult(
        base_price=base_price,
        final_price=final_price,
        discount_amount=discount_amount,
        applied_rules=applied,
        free_qty=free_qty,
    )
