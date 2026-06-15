from __future__ import annotations

import uuid
from datetime import datetime
from decimal import Decimal

import sqlalchemy as sa
from sqlalchemy import Boolean, DateTime, ForeignKey, Numeric, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.db import Base
from app.models.base import TimestampMixin


class Warehouse(Base, TimestampMixin):
    __tablename__ = "warehouses"
    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    tenant_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("tenants.id"))
    location_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("locations.id"), nullable=True)
    name: Mapped[str] = mapped_column(String(255))
    is_default: Mapped[bool] = mapped_column(Boolean, default=False)
    location: Mapped[Location | None] = relationship(back_populates="warehouses")  # noqa: F821
    stock_items: Mapped[list[StockItem]] = relationship(back_populates="warehouse")


class StockItem(Base, TimestampMixin):
    __tablename__ = "stock_items"
    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    product_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("products.id"))
    warehouse_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("warehouses.id"))
    qty: Mapped[Decimal] = mapped_column(Numeric(14, 3), default=Decimal("0"))
    reserved_qty: Mapped[Decimal] = mapped_column(Numeric(14, 3), default=Decimal("0"))
    min_stock: Mapped[Decimal] = mapped_column(Numeric(14, 3), default=Decimal("0"))
    max_stock: Mapped[Decimal | None] = mapped_column(Numeric(14, 3), nullable=True)
    __table_args__ = (UniqueConstraint("product_id", "warehouse_id", name="uq_stock_product_warehouse"),)
    product: Mapped[Product] = relationship(back_populates="stock_items")  # noqa: F821
    warehouse: Mapped[Warehouse] = relationship(back_populates="stock_items")


class StockMovement(Base, TimestampMixin):
    __tablename__ = "stock_movements"
    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    product_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("products.id"))
    warehouse_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("warehouses.id"))
    movement_type: Mapped[str] = mapped_column(String(20))
    qty: Mapped[Decimal] = mapped_column(Numeric(14, 3))
    reference_id: Mapped[uuid.UUID | None] = mapped_column(nullable=True)
    reference_type: Mapped[str | None] = mapped_column(String(50), nullable=True)
    device_id: Mapped[uuid.UUID | None] = mapped_column(nullable=True)
    location_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("locations.id"), nullable=True)
    note: Mapped[str | None] = mapped_column(String(500), nullable=True)
    occurred_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=sa.func.now())
