import uuid
from datetime import datetime
from decimal import Decimal

from app.schemas.base import BaseSchema, TimestampedRead


class FiscalRecordRead(TimestampedRead):
    sale_id: uuid.UUID
    location_id: uuid.UUID
    invoice_number: str
    business_premise_id: str
    electronic_device_id: str
    invoice_amount: Decimal
    tax_number: str | None
    issued_at: datetime
    zoi: str | None
    eor: str | None
    status: str
    confirmed_at: datetime | None
    error_message: str | None


class FiscalCounterRead(TimestampedRead):
    location_id: uuid.UUID
    business_premise_id: str
    electronic_device_id: str
    last_sequence: int


class FiscalizeRequest(BaseSchema):
    """Called by the sale endpoint after sale is created."""
    sale_id: uuid.UUID
    location_id: uuid.UUID
    invoice_amount: Decimal
