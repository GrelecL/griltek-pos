"""Edge-authoritative live state: stock, sync queue, cursors."""
import uuid
from datetime import datetime
from decimal import Decimal

import sqlalchemy as sa
from sqlalchemy import JSON, DateTime, Integer, Numeric, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from app.core.db import Base
from app.models.base import TimestampMixin


class EdgeStockItem(Base, TimestampMixin):
    __tablename__ = "edge_stock_items"
    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    product_id: Mapped[uuid.UUID] = mapped_column()
    qty: Mapped[Decimal] = mapped_column(Numeric(14, 3), default=Decimal("0"))
    reserved_qty: Mapped[Decimal] = mapped_column(Numeric(14, 3), default=Decimal("0"))
    min_stock: Mapped[Decimal] = mapped_column(Numeric(14, 3), default=Decimal("0"))
    __table_args__ = (UniqueConstraint("product_id", name="uq_edge_stock_product"),)


class EdgeStockMovement(Base, TimestampMixin):
    __tablename__ = "edge_stock_movements"
    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    product_id: Mapped[uuid.UUID] = mapped_column()
    movement_type: Mapped[str] = mapped_column(String(20))
    qty: Mapped[Decimal] = mapped_column(Numeric(14, 3))
    reference_id: Mapped[uuid.UUID | None] = mapped_column(nullable=True)
    reference_type: Mapped[str | None] = mapped_column(String(50), nullable=True)
    device_id: Mapped[uuid.UUID | None] = mapped_column(nullable=True)
    occurred_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=sa.func.now())
    synced_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)


class SyncQueueItem(Base, TimestampMixin):
    __tablename__ = "sync_queue"
    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    event_type: Mapped[str] = mapped_column(String(50))
    payload: Mapped[dict] = mapped_column(JSON)
    status: Mapped[str] = mapped_column(String(20), default="pending")
    attempts: Mapped[int] = mapped_column(Integer, default=0)
    last_attempted_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    error: Mapped[str | None] = mapped_column(String(500), nullable=True)


class SyncCursorRecord(Base, TimestampMixin):
    __tablename__ = "sync_cursors"
    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    entity_type: Mapped[str] = mapped_column(String(50), unique=True)
    pull_version: Mapped[int] = mapped_column(Integer, default=0)
    last_pulled_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
