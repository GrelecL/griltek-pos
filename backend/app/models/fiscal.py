import uuid
from datetime import datetime
from decimal import Decimal

import sqlalchemy as sa
from sqlalchemy import JSON, DateTime, ForeignKey, Integer, Numeric, String
from sqlalchemy.orm import Mapped, mapped_column

from app.core.db import Base
from app.models.base import TimestampMixin


class FiscalCounter(Base, TimestampMixin):
    """Durable per-device fiscal sequence counter. Single source of truth for gapless numbering."""
    __tablename__ = "fiscal_counters"
    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    location_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("locations.id"))
    # FURS identifiers
    business_premise_id: Mapped[str] = mapped_column(String(20))  # e.g. "PP001"
    electronic_device_id: Mapped[str] = mapped_column(String(20))  # e.g. "B1"
    last_sequence: Mapped[int] = mapped_column(Integer, default=0)
    # unique per location + premise + device
    __table_args__ = (
        sa.UniqueConstraint("location_id", "business_premise_id", "electronic_device_id",
                            name="uq_fiscal_counter"),
    )


class FiscalRecord(Base, TimestampMixin):
    """One record per fiscalized invoice. ZOI always present; EOR may be pending if offline."""
    __tablename__ = "fiscal_records"
    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    sale_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("sales.id"), unique=True)
    location_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("locations.id"))
    # Invoice number per ZDavPR: {business_premise_id}-{electronic_device_id}-{sequence}
    invoice_number: Mapped[str] = mapped_column(String(100))
    business_premise_id: Mapped[str] = mapped_column(String(20))
    electronic_device_id: Mapped[str] = mapped_column(String(20))
    invoice_amount: Mapped[Decimal] = mapped_column(Numeric(12, 2))
    tax_number: Mapped[str | None] = mapped_column(String(20), nullable=True)  # merchant tax number
    issued_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=sa.func.now())
    # ZOI: always computed locally (RSA-SHA256 → MD5). Never null if furs_enabled.
    zoi: Mapped[str | None] = mapped_column(String(32), nullable=True)
    # EOR: returned by FURS. Null while pending (offline).
    eor: Mapped[str | None] = mapped_column(String(36), nullable=True)
    status: Mapped[str] = mapped_column(String(20), default="pending")
    # confirmed | pending | failed | skipped
    furs_request: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    furs_response: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    confirmed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    error_message: Mapped[str | None] = mapped_column(String(500), nullable=True)
