"""Hospitality models: tables, open orders/tabs, KDS, courses."""
import uuid
from datetime import datetime
from decimal import Decimal

from sqlalchemy import JSON, DateTime, ForeignKey, Numeric, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.db import Base
from app.models.base import TimestampMixin


class FloorArea(Base, TimestampMixin):
    __tablename__ = "floor_areas"
    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    location_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("locations.id"))
    name: Mapped[str] = mapped_column(String(100))
    sort_order: Mapped[int] = mapped_column(default=0)
    tables: Mapped[list["Table"]] = relationship(back_populates="floor_area", cascade="all, delete-orphan")


class Table(Base, TimestampMixin):
    __tablename__ = "tables"
    __table_args__ = (UniqueConstraint("floor_area_id", "number"),)
    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    floor_area_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("floor_areas.id"))
    number: Mapped[str] = mapped_column(String(20))
    capacity: Mapped[int] = mapped_column(default=4)
    # status: free | occupied | reserved | cleaning
    status: Mapped[str] = mapped_column(String(20), default="free")
    pos_x: Mapped[int] = mapped_column(default=0)
    pos_y: Mapped[int] = mapped_column(default=0)
    floor_area: Mapped["FloorArea"] = relationship(back_populates="tables")
    orders: Mapped[list["Order"]] = relationship(back_populates="table")


class Order(Base, TimestampMixin):
    """Open tab / hospitality order before it materialises into a Sale."""
    __tablename__ = "orders"
    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    location_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("locations.id"))
    table_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("tables.id"), nullable=True)
    user_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("users.id"))
    # status: open | closed | cancelled
    status: Mapped[str] = mapped_column(String(20), default="open")
    # eat_in | take_away — affects VAT rate selection on materialise
    service_type: Mapped[str] = mapped_column(String(20), default="eat_in")
    covers: Mapped[int] = mapped_column(default=1)
    pager_number: Mapped[str | None] = mapped_column(String(20), nullable=True)
    note: Mapped[str | None] = mapped_column(String(500), nullable=True)
    # populated when materialised to a Sale
    sale_id: Mapped[uuid.UUID | None] = mapped_column(nullable=True)
    table: Mapped["Table | None"] = relationship(back_populates="orders")
    lines: Mapped[list["OrderLine"]] = relationship(back_populates="order", cascade="all, delete-orphan")


class OrderLine(Base, TimestampMixin):
    __tablename__ = "order_lines"
    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    order_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("orders.id"))
    product_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("products.id"))
    product_name: Mapped[str] = mapped_column(String(255))
    plu: Mapped[str] = mapped_column(String(50))
    qty: Mapped[Decimal] = mapped_column(Numeric(14, 3))
    unit_price: Mapped[Decimal] = mapped_column(Numeric(12, 4))
    vat_rate: Mapped[Decimal] = mapped_column(Numeric(6, 3))
    line_total: Mapped[Decimal] = mapped_column(Numeric(12, 2))
    # course number (null = no courses / fire immediately)
    course: Mapped[int | None] = mapped_column(nullable=True)
    # kds_status: pending | in_kitchen | ready | served
    kds_status: Mapped[str] = mapped_column(String(20), default="pending")
    kds_station: Mapped[str | None] = mapped_column(String(50), nullable=True)
    fired_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    ready_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    served_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    note: Mapped[str | None] = mapped_column(String(300), nullable=True)
    modifiers: Mapped[list] = mapped_column(JSON, default=list)
    order: Mapped["Order"] = relationship(back_populates="lines")


class KDSStation(Base, TimestampMixin):
    """Named kitchen station (e.g. grill, cold, bar)."""
    __tablename__ = "kds_stations"
    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    location_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("locations.id"))
    name: Mapped[str] = mapped_column(String(100))
    # category_ids this station handles (JSON list of UUIDs as strings)
    category_ids: Mapped[list] = mapped_column(JSON, default=list)
    is_active: Mapped[bool] = mapped_column(default=True)
