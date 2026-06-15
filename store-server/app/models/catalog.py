"""Edge replica of catalog master data — written only by sync engine."""
import uuid
from decimal import Decimal

import sqlalchemy as sa
from sqlalchemy import Boolean, ForeignKey, Integer, Numeric, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.db import Base
from app.models.base import TimestampMixin


class Category(Base, TimestampMixin):
    __tablename__ = "edge_categories"
    id: Mapped[uuid.UUID] = mapped_column(primary_key=True)
    cloud_id: Mapped[uuid.UUID] = mapped_column(unique=True)
    tenant_id: Mapped[uuid.UUID] = mapped_column()
    name: Mapped[str] = mapped_column(String(255))
    slug: Mapped[str] = mapped_column(String(100))
    parent_id: Mapped[uuid.UUID | None] = mapped_column(nullable=True)
    sort_order: Mapped[int] = mapped_column(Integer, default=0)


class Product(Base, TimestampMixin):
    __tablename__ = "edge_products"
    id: Mapped[uuid.UUID] = mapped_column(primary_key=True)
    cloud_id: Mapped[uuid.UUID] = mapped_column(unique=True)
    tenant_id: Mapped[uuid.UUID] = mapped_column()
    plu: Mapped[str] = mapped_column(String(50))
    name: Mapped[str] = mapped_column(String(255))
    vat_rate: Mapped[Decimal] = mapped_column(Numeric(5, 2), default=Decimal("22"))
    unit: Mapped[str] = mapped_column(String(10), default="piece")
    is_weighable: Mapped[bool] = mapped_column(Boolean, default=False)
    weight_grams: Mapped[int | None] = mapped_column(Integer, nullable=True)
    weight_tolerance_pct: Mapped[Decimal | None] = mapped_column(Numeric(5, 2), nullable=True)
    age_restricted: Mapped[bool] = mapped_column(Boolean, default=False)
    min_age: Mapped[int | None] = mapped_column(Integer, nullable=True)
    allergens: Mapped[list] = mapped_column(sa.JSON, default=list)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    barcodes: Mapped[list["Barcode"]] = relationship(back_populates="product")
    prices: Mapped[list["Price"]] = relationship(back_populates="product")


class Barcode(Base, TimestampMixin):
    __tablename__ = "edge_barcodes"
    id: Mapped[uuid.UUID] = mapped_column(primary_key=True)
    cloud_id: Mapped[uuid.UUID] = mapped_column(unique=True)
    product_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("edge_products.id"))
    code: Mapped[str] = mapped_column(String(100), unique=True)
    barcode_type: Mapped[str] = mapped_column(String(20), default="ean13")
    product: Mapped["Product"] = relationship(back_populates="barcodes")


class Price(Base, TimestampMixin):
    __tablename__ = "edge_prices"
    id: Mapped[uuid.UUID] = mapped_column(primary_key=True)
    cloud_id: Mapped[uuid.UUID] = mapped_column(unique=True)
    product_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("edge_products.id"))
    price_type: Mapped[str] = mapped_column(String(20), default="regular")
    amount: Mapped[Decimal] = mapped_column(Numeric(10, 2))
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    product: Mapped["Product"] = relationship(back_populates="prices")
