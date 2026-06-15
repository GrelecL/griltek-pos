import uuid
from datetime import datetime
from decimal import Decimal

import sqlalchemy as sa
from sqlalchemy import DateTime, ForeignKey, Numeric, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.db import Base
from app.models.base import TimestampMixin


class CashSession(Base, TimestampMixin):
    __tablename__ = "cash_sessions"
    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    location_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("locations.id"))
    device_id: Mapped[uuid.UUID | None] = mapped_column(nullable=True)
    user_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("users.id"))
    status: Mapped[str] = mapped_column(String(20), default="open")
    opening_float: Mapped[Decimal] = mapped_column(Numeric(12, 2), default=Decimal("0"))
    closing_float: Mapped[Decimal | None] = mapped_column(Numeric(12, 2), nullable=True)
    cash_in: Mapped[Decimal] = mapped_column(Numeric(12, 2), default=Decimal("0"))
    cash_out: Mapped[Decimal] = mapped_column(Numeric(12, 2), default=Decimal("0"))
    opened_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=sa.func.now())
    closed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    note: Mapped[str | None] = mapped_column(String(500), nullable=True)
    sales: Mapped[list["Sale"]] = relationship(back_populates="cash_session")


class Sale(Base, TimestampMixin):
    __tablename__ = "sales"
    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    transaction_uuid: Mapped[uuid.UUID] = mapped_column(unique=True, default=uuid.uuid4)
    cash_session_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("cash_sessions.id"))
    location_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("locations.id"))
    device_id: Mapped[uuid.UUID | None] = mapped_column(nullable=True)
    user_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("users.id"))
    customer_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("customers.id"), nullable=True)
    sale_type: Mapped[str] = mapped_column(String(20), default="sale")
    status: Mapped[str] = mapped_column(String(20), default="completed")
    subtotal: Mapped[Decimal] = mapped_column(Numeric(12, 2))
    discount_total: Mapped[Decimal] = mapped_column(Numeric(12, 2), default=Decimal("0"))
    vat_total: Mapped[Decimal] = mapped_column(Numeric(12, 2))
    total: Mapped[Decimal] = mapped_column(Numeric(12, 2))
    original_sale_id: Mapped[uuid.UUID | None] = mapped_column(nullable=True)
    note: Mapped[str | None] = mapped_column(String(500), nullable=True)
    completed_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=sa.func.now())
    cash_session: Mapped["CashSession"] = relationship(back_populates="sales")
    lines: Mapped[list["SaleLine"]] = relationship(back_populates="sale", cascade="all, delete-orphan")
    payments: Mapped[list["Payment"]] = relationship(back_populates="sale", cascade="all, delete-orphan")


class SaleLine(Base, TimestampMixin):
    __tablename__ = "sale_lines"
    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    sale_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("sales.id"))
    product_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("products.id"))
    product_name: Mapped[str] = mapped_column(String(255))
    plu: Mapped[str] = mapped_column(String(50))
    qty: Mapped[Decimal] = mapped_column(Numeric(14, 3))
    unit_price: Mapped[Decimal] = mapped_column(Numeric(10, 4))
    vat_rate: Mapped[Decimal] = mapped_column(Numeric(5, 2))
    discount_pct: Mapped[Decimal] = mapped_column(Numeric(5, 2), default=Decimal("0"))
    discount_amount: Mapped[Decimal] = mapped_column(Numeric(10, 4), default=Decimal("0"))
    line_total: Mapped[Decimal] = mapped_column(Numeric(12, 2))
    vat_amount: Mapped[Decimal] = mapped_column(Numeric(10, 4))
    modifiers: Mapped[list] = mapped_column(sa.JSON, default=list)
    sale: Mapped["Sale"] = relationship(back_populates="lines")


class Payment(Base, TimestampMixin):
    __tablename__ = "payments"
    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    sale_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("sales.id"))
    method: Mapped[str] = mapped_column(String(20))
    amount: Mapped[Decimal] = mapped_column(Numeric(12, 2))
    status: Mapped[str] = mapped_column(String(20), default="completed")
    reference: Mapped[str | None] = mapped_column(String(255), nullable=True)
    change_given: Mapped[Decimal] = mapped_column(Numeric(12, 2), default=Decimal("0"))
    sale: Mapped["Sale"] = relationship(back_populates="payments")
