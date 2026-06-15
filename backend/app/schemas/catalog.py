import uuid
from datetime import datetime
from decimal import Decimal

from app.schemas.base import BaseSchema, TimestampedRead


class CategoryCreate(BaseSchema):
    tenant_id: uuid.UUID
    name: str
    slug: str
    parent_id: uuid.UUID | None = None
    sort_order: int = 0


class CategoryRead(TimestampedRead):
    tenant_id: uuid.UUID
    name: str
    slug: str
    parent_id: uuid.UUID | None
    sort_order: int


class CategoryUpdate(BaseSchema):
    name: str | None = None
    slug: str | None = None
    parent_id: uuid.UUID | None = None
    sort_order: int | None = None


class ProductCreate(BaseSchema):
    tenant_id: uuid.UUID
    category_id: uuid.UUID | None = None
    plu: str
    name: str
    description: str | None = None
    vat_rate: Decimal = Decimal("22")
    unit: str = "piece"
    is_weighable: bool = False
    weight_grams: int | None = None
    weight_tolerance_pct: Decimal | None = None
    age_restricted: bool = False
    min_age: int | None = None
    allergens: list[str] = []
    modifiers: list[dict] = []
    image_url: str | None = None
    is_active: bool = True


class ProductRead(TimestampedRead):
    tenant_id: uuid.UUID
    category_id: uuid.UUID | None
    plu: str
    name: str
    description: str | None
    vat_rate: Decimal
    unit: str
    is_weighable: bool
    weight_grams: int | None
    weight_tolerance_pct: Decimal | None
    age_restricted: bool
    min_age: int | None
    allergens: list
    modifiers: list
    image_url: str | None
    is_active: bool


class ProductUpdate(BaseSchema):
    category_id: uuid.UUID | None = None
    name: str | None = None
    description: str | None = None
    vat_rate: Decimal | None = None
    unit: str | None = None
    is_weighable: bool | None = None
    weight_grams: int | None = None
    weight_tolerance_pct: Decimal | None = None
    age_restricted: bool | None = None
    min_age: int | None = None
    allergens: list[str] | None = None
    modifiers: list[dict] | None = None
    image_url: str | None = None
    is_active: bool | None = None


class BarcodeCreate(BaseSchema):
    product_id: uuid.UUID
    code: str
    barcode_type: str = "ean13"


class BarcodeRead(TimestampedRead):
    product_id: uuid.UUID
    code: str
    barcode_type: str


class PriceCreate(BaseSchema):
    product_id: uuid.UUID
    location_id: uuid.UUID | None = None
    price_type: str = "regular"
    amount: Decimal
    valid_from: datetime | None = None
    valid_until: datetime | None = None
    min_qty: int = 1
    is_active: bool = True


class PriceRead(TimestampedRead):
    product_id: uuid.UUID
    location_id: uuid.UUID | None
    price_type: str
    amount: Decimal
    valid_from: datetime | None
    valid_until: datetime | None
    min_qty: int
    is_active: bool


class PriceUpdate(BaseSchema):
    amount: Decimal | None = None
    valid_from: datetime | None = None
    valid_until: datetime | None = None
    is_active: bool | None = None
