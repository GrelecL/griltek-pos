from __future__ import annotations

import uuid
from datetime import datetime
from decimal import Decimal

import sqlalchemy as sa
from sqlalchemy import DateTime, ForeignKey, Numeric, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.db import Base
from app.models.base import TimestampMixin


class Tenant(Base, TimestampMixin):
    __tablename__ = "tenants"
    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    name: Mapped[str] = mapped_column(String(255))
    slug: Mapped[str] = mapped_column(String(100), unique=True)
    # relationships
    locations: Mapped[list[Location]] = relationship(back_populates="tenant")  # noqa: F821
    subscriptions: Mapped[list[Subscription]] = relationship(back_populates="tenant")


class Plan(Base, TimestampMixin):
    __tablename__ = "plans"
    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    name: Mapped[str] = mapped_column(String(100))
    max_locations: Mapped[int] = mapped_column(default=1)
    max_devices: Mapped[int] = mapped_column(default=5)
    price_monthly: Mapped[Decimal] = mapped_column(Numeric(10, 2), default=Decimal("0"))
    features: Mapped[dict] = mapped_column(sa.JSON, default=dict)
    subscriptions: Mapped[list[Subscription]] = relationship(back_populates="plan")


class Subscription(Base, TimestampMixin):
    __tablename__ = "subscriptions"
    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    tenant_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("tenants.id"))
    plan_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("plans.id"))
    status: Mapped[str] = mapped_column(String(20), default="trial")
    period_start: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    period_end: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    billing_reference: Mapped[str | None] = mapped_column(String(255), nullable=True)
    tenant: Mapped[Tenant] = relationship(back_populates="subscriptions")
    plan: Mapped[Plan] = relationship(back_populates="subscriptions")
