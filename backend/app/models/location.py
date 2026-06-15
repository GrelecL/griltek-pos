from __future__ import annotations

import uuid
from decimal import Decimal

from sqlalchemy import Boolean, ForeignKey, Numeric, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.db import Base
from app.models.base import TimestampMixin


class Location(Base, TimestampMixin):
    __tablename__ = "locations"
    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    tenant_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("tenants.id"))
    name: Mapped[str] = mapped_column(String(255))
    address: Mapped[str | None] = mapped_column(String(500), nullable=True)
    business_type: Mapped[str] = mapped_column(String(20), default="retail")
    furs_business_premise_id: Mapped[str | None] = mapped_column(String(100), nullable=True)
    furs_tax_number: Mapped[str | None] = mapped_column(String(20), nullable=True)
    timezone: Mapped[str] = mapped_column(String(50), default="Europe/Ljubljana")
    tenant: Mapped[Tenant] = relationship(back_populates="locations")  # noqa: F821
    config: Mapped[LocationConfig | None] = relationship(back_populates="location", uselist=False)
    warehouses: Mapped[list[Warehouse]] = relationship(back_populates="location")  # noqa: F821


class LocationConfig(Base, TimestampMixin):
    __tablename__ = "location_configs"
    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    location_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("locations.id"), unique=True)
    # Feature toggles
    self_checkout: Mapped[bool] = mapped_column(Boolean, default=False)
    price_check: Mapped[bool] = mapped_column(Boolean, default=False)
    order_kiosk: Mapped[bool] = mapped_column(Boolean, default=False)
    kds: Mapped[bool] = mapped_column(Boolean, default=False)
    tables: Mapped[bool] = mapped_column(Boolean, default=False)
    open_tabs: Mapped[bool] = mapped_column(Boolean, default=False)
    courses: Mapped[bool] = mapped_column(Boolean, default=False)
    tips: Mapped[bool] = mapped_column(Boolean, default=False)
    security_scale: Mapped[bool] = mapped_column(Boolean, default=False)
    # VAT / fiscal
    vat_eat_in: Mapped[Decimal] = mapped_column(Numeric(5, 2), default=Decimal("9.5"))
    vat_take_away: Mapped[Decimal] = mapped_column(Numeric(5, 2), default=Decimal("9.5"))
    currency: Mapped[str] = mapped_column(String(3), default="EUR")
    cash_rounding: Mapped[bool] = mapped_column(Boolean, default=False)
    furs_enabled: Mapped[bool] = mapped_column(Boolean, default=True)
    location: Mapped[Location] = relationship(back_populates="config")
