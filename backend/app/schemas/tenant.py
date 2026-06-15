import uuid
from decimal import Decimal

from app.schemas.base import BaseSchema, TimestampedRead


class TenantCreate(BaseSchema):
    name: str
    slug: str


class TenantRead(TimestampedRead):
    name: str
    slug: str


class LocationCreate(BaseSchema):
    tenant_id: uuid.UUID
    name: str
    address: str | None = None
    business_type: str = "retail"
    furs_business_premise_id: str | None = None
    furs_tax_number: str | None = None
    timezone: str = "Europe/Ljubljana"


class LocationRead(TimestampedRead):
    tenant_id: uuid.UUID
    name: str
    address: str | None
    business_type: str
    furs_business_premise_id: str | None
    furs_tax_number: str | None
    timezone: str


class LocationConfigRead(TimestampedRead):
    location_id: uuid.UUID
    self_checkout: bool
    price_check: bool
    order_kiosk: bool
    kds: bool
    tables: bool
    open_tabs: bool
    courses: bool
    tips: bool
    security_scale: bool
    vat_eat_in: Decimal
    vat_take_away: Decimal
    currency: str
    cash_rounding: bool
    furs_enabled: bool = True


class LocationConfigUpdate(BaseSchema):
    self_checkout: bool | None = None
    price_check: bool | None = None
    order_kiosk: bool | None = None
    kds: bool | None = None
    tables: bool | None = None
    open_tabs: bool | None = None
    courses: bool | None = None
    tips: bool | None = None
    security_scale: bool | None = None
    vat_eat_in: Decimal | None = None
    vat_take_away: Decimal | None = None
    currency: str | None = None
    cash_rounding: bool | None = None
    furs_enabled: bool | None = None
