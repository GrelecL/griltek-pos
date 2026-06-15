from __future__ import annotations

import uuid
from datetime import datetime

import sqlalchemy as sa
from sqlalchemy import Boolean, DateTime, ForeignKey, Integer, String
from sqlalchemy.orm import Mapped, mapped_column

from app.core.db import Base
from app.models.base import TimestampMixin


class PricingRule(Base, TimestampMixin):
    __tablename__ = "pricing_rules"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    tenant_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("tenants.id"))
    name: Mapped[str] = mapped_column(String(120))
    rule_type: Mapped[str] = mapped_column(String(30))
    # pct_discount | fixed_discount | fixed_price | bxgy
    priority: Mapped[int] = mapped_column(Integer, default=100)
    # Lower number = applied first.
    # conditions JSON keys (all optional):
    #   product_ids: list[str]      — applies only to these product UUIDs
    #   category_ids: list[str]     — applies to products in these categories
    #   min_qty: int                — minimum quantity in cart line
    #   customer_tiers: list[str]   — e.g. ["gold", "silver"]
    #   time_from: "HH:MM"          — start of daily time window
    #   time_to: "HH:MM"            — end of daily time window
    #   days_of_week: list[int]     — 0=Mon … 6=Sun
    conditions: Mapped[dict] = mapped_column(sa.JSON, default=dict)
    # action JSON keys:
    #   value: float               — pct / amount / fixed price
    #   free_qty: int              — for bxgy: how many free items per qualifying set
    action: Mapped[dict] = mapped_column(sa.JSON, default=dict)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    # stackable=False stops rule evaluation after this rule fires
    stackable: Mapped[bool] = mapped_column(Boolean, default=True)
    valid_from: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    valid_until: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
