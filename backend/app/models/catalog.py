from __future__ import annotations

import uuid
from datetime import datetime
from decimal import Decimal

import sqlalchemy as sa
from sqlalchemy import Boolean, DateTime, ForeignKey, Integer, Numeric, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.db import Base
from app.models.base import TimestampMixin


class Category(Base, TimestampMixin):
    __tablename__ = "categories"
    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    tenant_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("tenants.id"))
    parent_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("categories.id"), nullable=True)
    name: Mapped[str] = mapped_column(String(255))
    slug: Mapped[str] = mapped_column(String(100))
    sort_order: Mapped[int] = mapped_column(Integer, default=0)
    __table_args__ = (UniqueConstraint("tenant_id", "slug", name="uq_category_tenant_slug"),)
    products: Mapped[list[Product]] = relationship(back_populates="category")
    children: Mapped[list[Category]] = relationship(back_populates="parent")
    parent: Mapped[Category | None] = relationship(back_populates="children", remote_side=[id])  # type: ignore


class Product(Base, TimestampMixin):
    __tablename__ = "products"
    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    tenant_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("tenants.id"))
    category_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("categories.id"), nullable=True)
    plu: Mapped[str] = mapped_column(String(50))
    name: Mapped[str] = mapped_column(String(255))
    description: Mapped[str | None] = mapped_column(String(2000), nullable=True)
    vat_rate: Mapped[Decimal] = mapped_column(Numeric(5, 2), default=Decimal("22"))
    unit: Mapped[str] = mapped_column(String(10), default="piece")
    is_weighable: Mapped[bool] = mapped_column(Boolean, default=False)
    weight_grams: Mapped[int | None] = mapped_column(Integer, nullable=True)
    weight_tolerance_pct: Mapped[Decimal | None] = mapped_column(Numeric(5, 2), nullable=True)
    age_restricted: Mapped[bool] = mapped_column(Boolean, default=False)
    min_age: Mapped[int | None] = mapped_column(Integer, nullable=True)
    allergens: Mapped[list] = mapped_column(sa.JSON, default=list)
    modifiers: Mapped[list] = mapped_column(sa.JSON, default=list)
    image_url: Mapped[str | None] = mapped_column(String(1000), nullable=True)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    __table_args__ = (UniqueConstraint("tenant_id", "plu", name="uq_product_tenant_plu"),)
    category: Mapped[Category | None] = relationship(back_populates="products")
    barcodes: Mapped[list[Barcode]] = relationship(back_populates="product")
    prices: Mapped[list[Price]] = relationship(back_populates="product")
    stock_items: Mapped[list[StockItem]] = relationship(back_populates="product")  # noqa: F821


class Barcode(Base, TimestampMixin):
    __tablename__ = "barcodes"
    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    product_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("products.id"))
    code: Mapped[str] = mapped_column(String(100), unique=True)
    barcode_type: Mapped[str] = mapped_column(String(20), default="ean13")
    product: Mapped[Product] = relationship(back_populates="barcodes")


class Price(Base, TimestampMixin):
    __tablename__ = "prices"
    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    product_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("products.id"))
    location_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("locations.id"), nullable=True)
    price_type: Mapped[str] = mapped_column(String(20), default="regular")
    amount: Mapped[Decimal] = mapped_column(Numeric(10, 2))
    valid_from: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    valid_until: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    min_qty: Mapped[int] = mapped_column(Integer, default=1)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    product: Mapped[Product] = relationship(back_populates="prices")
