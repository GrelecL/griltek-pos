import uuid
from datetime import datetime
from decimal import Decimal

from app.schemas.base import BaseSchema, TimestampedRead


class CashSessionOpen(BaseSchema):
    location_id: uuid.UUID
    device_id: uuid.UUID | None = None
    user_id: uuid.UUID
    opening_float: Decimal = Decimal("0")


class CashAdjustment(BaseSchema):
    amount: Decimal
    note: str | None = None


class CashSessionClose(BaseSchema):
    closing_float: Decimal
    note: str | None = None


class CashSessionRead(TimestampedRead):
    location_id: uuid.UUID
    device_id: uuid.UUID | None
    user_id: uuid.UUID
    status: str
    opening_float: Decimal
    closing_float: Decimal | None
    cash_in: Decimal
    cash_out: Decimal
    opened_at: datetime
    closed_at: datetime | None
    note: str | None


class XReport(BaseSchema):
    """Intermediate (X) report — does not close session."""
    session_id: uuid.UUID
    generated_at: datetime
    total_sales: Decimal
    total_returns: Decimal
    net_sales: Decimal
    cash_sales: Decimal
    card_sales: Decimal
    other_sales: Decimal
    sale_count: int
    return_count: int
    opening_float: Decimal
    cash_in: Decimal
    cash_out: Decimal
    expected_cash: Decimal


class ZReport(XReport):
    """Z (closing) report — session must be closed first."""
    closed_at: datetime


class SaleLineCreate(BaseSchema):
    product_id: uuid.UUID
    product_name: str
    plu: str
    qty: Decimal
    unit_price: Decimal
    vat_rate: Decimal
    discount_pct: Decimal = Decimal("0")
    discount_amount: Decimal = Decimal("0")
    modifiers: list[dict] = []


class SaleLineRead(TimestampedRead):
    sale_id: uuid.UUID
    product_id: uuid.UUID
    product_name: str
    plu: str
    qty: Decimal
    unit_price: Decimal
    vat_rate: Decimal
    discount_pct: Decimal
    discount_amount: Decimal
    line_total: Decimal
    vat_amount: Decimal
    modifiers: list


class PaymentCreate(BaseSchema):
    method: str
    amount: Decimal
    reference: str | None = None
    change_given: Decimal = Decimal("0")


class PaymentRead(TimestampedRead):
    sale_id: uuid.UUID
    method: str
    amount: Decimal
    status: str
    reference: str | None
    change_given: Decimal


class SaleCreate(BaseSchema):
    transaction_uuid: uuid.UUID
    cash_session_id: uuid.UUID
    location_id: uuid.UUID
    device_id: uuid.UUID | None = None
    user_id: uuid.UUID
    customer_id: uuid.UUID | None = None
    sale_type: str = "sale"
    note: str | None = None
    lines: list[SaleLineCreate]
    payments: list[PaymentCreate]


class SaleRead(TimestampedRead):
    transaction_uuid: uuid.UUID
    cash_session_id: uuid.UUID
    location_id: uuid.UUID
    device_id: uuid.UUID | None
    user_id: uuid.UUID
    customer_id: uuid.UUID | None
    sale_type: str
    status: str
    subtotal: Decimal
    discount_total: Decimal
    vat_total: Decimal
    total: Decimal
    original_sale_id: uuid.UUID | None
    note: str | None
    completed_at: datetime
    lines: list[SaleLineRead] = []
    payments: list[PaymentRead] = []
