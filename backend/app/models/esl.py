from __future__ import annotations

import uuid
from datetime import datetime
from decimal import Decimal

from sqlalchemy import DateTime, ForeignKey, Numeric, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from app.core.db import Base
from app.models.base import TimestampMixin


class ESLDevice(Base, TimestampMixin):
    """Physical electronic shelf label unit."""
    __tablename__ = "esl_devices"
    __table_args__ = (UniqueConstraint("location_id", "esl_id", name="uq_esl_location_id"),)

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    location_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("locations.id"))
    # hardware device identifier assigned by the ESL gateway
    esl_id: Mapped[str] = mapped_column(String(100))
    product_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("products.id"), nullable=True)
    # pending | synced | error | offline
    status: Mapped[str] = mapped_column(String(20), default="pending")
    last_synced_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    last_price: Mapped[Decimal | None] = mapped_column(Numeric(10, 2), nullable=True)
    last_error: Mapped[str | None] = mapped_column(String(255), nullable=True)
