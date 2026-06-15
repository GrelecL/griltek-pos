"""Pricing rules API."""
from __future__ import annotations

import uuid
from datetime import datetime
from decimal import Decimal
from typing import Any

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.db import get_db
from app.models.pricing import PricingRule
from app.services.pricing import compute_price, get_active_rules, get_base_price

router = APIRouter(prefix="/pricing", tags=["pricing"])


class PricingRuleCreate(BaseModel):
    tenant_id: uuid.UUID
    name: str
    rule_type: str  # pct_discount | fixed_discount | fixed_price | bxgy
    priority: int = 100
    conditions: dict[str, Any] = {}
    action: dict[str, Any]
    stackable: bool = True
    valid_from: datetime | None = None
    valid_until: datetime | None = None


class PricingRuleUpdate(BaseModel):
    name: str | None = None
    priority: int | None = None
    conditions: dict[str, Any] | None = None
    action: dict[str, Any] | None = None
    stackable: bool | None = None
    is_active: bool | None = None
    valid_from: datetime | None = None
    valid_until: datetime | None = None


class PricePreviewRequest(BaseModel):
    product_id: uuid.UUID
    tenant_id: uuid.UUID
    qty: Decimal = Decimal("1")
    location_id: uuid.UUID | None = None
    customer_tier: str | None = None


@router.post("/rules", status_code=201)
async def create_rule(body: PricingRuleCreate, db: AsyncSession = Depends(get_db)):
    rule = PricingRule(id=uuid.uuid4(), **body.model_dump())
    db.add(rule)
    await db.commit()
    return {"id": str(rule.id), "name": rule.name, "rule_type": rule.rule_type, "priority": rule.priority}


@router.get("/rules")
async def list_rules(tenant_id: uuid.UUID, db: AsyncSession = Depends(get_db)):
    result = await db.execute(
        select(PricingRule)
        .where(PricingRule.tenant_id == tenant_id)
        .order_by(PricingRule.priority)
    )
    rules = result.scalars().all()
    return [
        {
            "id": str(r.id), "name": r.name, "rule_type": r.rule_type,
            "priority": r.priority, "is_active": r.is_active,
            "stackable": r.stackable, "conditions": r.conditions, "action": r.action,
            "valid_from": r.valid_from.isoformat() if r.valid_from else None,
            "valid_until": r.valid_until.isoformat() if r.valid_until else None,
        }
        for r in rules
    ]


@router.put("/rules/{rule_id}")
async def update_rule(rule_id: uuid.UUID, body: PricingRuleUpdate, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(PricingRule).where(PricingRule.id == rule_id))
    rule = result.scalar_one_or_none()
    if not rule:
        raise HTTPException(404, "Rule not found")
    for field, value in body.model_dump(exclude_none=True).items():
        setattr(rule, field, value)
    await db.commit()
    return {"id": str(rule.id), "name": rule.name, "is_active": rule.is_active}


@router.delete("/rules/{rule_id}", status_code=204)
async def deactivate_rule(rule_id: uuid.UUID, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(PricingRule).where(PricingRule.id == rule_id))
    rule = result.scalar_one_or_none()
    if not rule:
        raise HTTPException(404, "Rule not found")
    rule.is_active = False
    await db.commit()


@router.post("/preview")
async def preview_price(body: PricePreviewRequest, db: AsyncSession = Depends(get_db)):
    base = await get_base_price(db, body.product_id, body.qty, location_id=body.location_id)
    if base is None:
        raise HTTPException(404, "No active price found for this product")
    result = await compute_price(
        db, body.product_id, base, body.qty,
        tenant_id=body.tenant_id,
        customer_tier=body.customer_tier,
    )
    return {
        "product_id": str(body.product_id),
        "qty": str(body.qty),
        "base_price": str(result.base_price),
        "final_price": str(result.final_price),
        "discount_amount": str(result.discount_amount),
        "applied_rules": result.applied_rules,
        "free_qty": result.free_qty,
    }


@router.get("/active")
async def active_rules(tenant_id: uuid.UUID, db: AsyncSession = Depends(get_db)):
    rules = await get_active_rules(db, tenant_id)
    return [{"id": str(r.id), "name": r.name, "rule_type": r.rule_type, "priority": r.priority} for r in rules]
