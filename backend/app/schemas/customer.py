import uuid
from decimal import Decimal

from app.schemas.base import BaseSchema, TimestampedRead


class CustomerCreate(BaseSchema):
    tenant_id: uuid.UUID
    name: str
    tax_id: str | None = None
    address: str | None = None
    email: str | None = None
    phone: str | None = None
    is_b2b: bool = False


class CustomerRead(TimestampedRead):
    tenant_id: uuid.UUID
    name: str
    tax_id: str | None
    address: str | None
    email: str | None
    phone: str | None
    is_b2b: bool


class CustomerUpdate(BaseSchema):
    name: str | None = None
    tax_id: str | None = None
    address: str | None = None
    email: str | None = None
    phone: str | None = None
    is_b2b: bool | None = None


class CreditAccountCreate(BaseSchema):
    customer_id: uuid.UUID
    credit_limit: Decimal = Decimal("0")


class CreditAccountRead(TimestampedRead):
    customer_id: uuid.UUID
    credit_limit: Decimal
    balance: Decimal
    is_active: bool
