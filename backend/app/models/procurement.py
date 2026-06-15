import uuid
from datetime import datetime
from decimal import Decimal

import sqlalchemy as sa
from sqlalchemy import Boolean, DateTime, ForeignKey, Numeric, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.db import Base
from app.models.base import TimestampMixin


class Supplier(Base, TimestampMixin):
    __tablename__ = "suppliers"
    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    tenant_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("tenants.id"))
    name: Mapped[str] = mapped_column(String(255))
    contact_name: Mapped[str | None] = mapped_column(String(255), nullable=True)
    email: Mapped[str | None] = mapped_column(String(255), nullable=True)
    phone: Mapped[str | None] = mapped_column(String(50), nullable=True)
    address: Mapped[str | None] = mapped_column(String(500), nullable=True)
    tax_id: Mapped[str | None] = mapped_column(String(50), nullable=True)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    purchase_orders: Mapped[list["PurchaseOrder"]] = relationship(back_populates="supplier")


class PurchaseOrder(Base, TimestampMixin):
    __tablename__ = "purchase_orders"
    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    tenant_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("tenants.id"))
    supplier_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("suppliers.id"))
    warehouse_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("warehouses.id"))
    status: Mapped[str] = mapped_column(String(20), default="draft")  # draft|ordered|partial|received|cancelled
    order_number: Mapped[str | None] = mapped_column(String(100), nullable=True)
    ordered_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    expected_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    note: Mapped[str | None] = mapped_column(String(1000), nullable=True)
    supplier: Mapped["Supplier"] = relationship(back_populates="purchase_orders")
    lines: Mapped[list["PurchaseOrderLine"]] = relationship(back_populates="order", cascade="all, delete-orphan")
    receipts: Mapped[list["GoodsReceipt"]] = relationship(back_populates="order")


class PurchaseOrderLine(Base, TimestampMixin):
    __tablename__ = "purchase_order_lines"
    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    order_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("purchase_orders.id"))
    product_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("products.id"))
    qty_ordered: Mapped[Decimal] = mapped_column(Numeric(14, 3))
    qty_received: Mapped[Decimal] = mapped_column(Numeric(14, 3), default=Decimal("0"))
    unit_cost: Mapped[Decimal] = mapped_column(Numeric(10, 4))
    order: Mapped["PurchaseOrder"] = relationship(back_populates="lines")


class GoodsReceipt(Base, TimestampMixin):
    __tablename__ = "goods_receipts"
    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    order_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("purchase_orders.id"))
    warehouse_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("warehouses.id"))
    received_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=sa.func.now())
    note: Mapped[str | None] = mapped_column(String(1000), nullable=True)
    order: Mapped["PurchaseOrder"] = relationship(back_populates="receipts")
    lines: Mapped[list["GoodsReceiptLine"]] = relationship(back_populates="receipt", cascade="all, delete-orphan")


class GoodsReceiptLine(Base, TimestampMixin):
    __tablename__ = "goods_receipt_lines"
    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    receipt_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("goods_receipts.id"))
    order_line_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("purchase_order_lines.id"))
    product_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("products.id"))
    qty_received: Mapped[Decimal] = mapped_column(Numeric(14, 3))
    unit_cost: Mapped[Decimal] = mapped_column(Numeric(10, 4))
    receipt: Mapped["GoodsReceipt"] = relationship(back_populates="lines")


class Transfer(Base, TimestampMixin):
    __tablename__ = "transfers"
    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    tenant_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("tenants.id"))
    from_warehouse_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("warehouses.id"))
    to_warehouse_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("warehouses.id"))
    status: Mapped[str] = mapped_column(String(20), default="pending")  # pending|completed|cancelled
    transferred_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    note: Mapped[str | None] = mapped_column(String(1000), nullable=True)
    lines: Mapped[list["TransferLine"]] = relationship(back_populates="transfer", cascade="all, delete-orphan")


class TransferLine(Base, TimestampMixin):
    __tablename__ = "transfer_lines"
    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    transfer_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("transfers.id"))
    product_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("products.id"))
    qty: Mapped[Decimal] = mapped_column(Numeric(14, 3))
    transfer: Mapped["Transfer"] = relationship(back_populates="lines")


class StockTake(Base, TimestampMixin):
    __tablename__ = "stock_takes"
    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    tenant_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("tenants.id"))
    warehouse_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("warehouses.id"))
    status: Mapped[str] = mapped_column(String(20), default="open")  # open|counting|completed|cancelled
    started_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=sa.func.now())
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    note: Mapped[str | None] = mapped_column(String(1000), nullable=True)
    lines: Mapped[list["StockTakeLine"]] = relationship(back_populates="stock_take", cascade="all, delete-orphan")


class StockTakeLine(Base, TimestampMixin):
    __tablename__ = "stock_take_lines"
    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    stock_take_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("stock_takes.id"))
    product_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("products.id"))
    qty_system: Mapped[Decimal] = mapped_column(Numeric(14, 3))   # qty at time of take
    qty_counted: Mapped[Decimal | None] = mapped_column(Numeric(14, 3), nullable=True)
    qty_difference: Mapped[Decimal | None] = mapped_column(Numeric(14, 3), nullable=True)  # counted - system
    stock_take: Mapped["StockTake"] = relationship(back_populates="lines")
