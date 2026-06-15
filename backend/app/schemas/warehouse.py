import uuid
from datetime import datetime
from decimal import Decimal

from app.schemas.base import BaseSchema, TimestampedRead


class WarehouseCreate(BaseSchema):
    tenant_id: uuid.UUID
    location_id: uuid.UUID | None = None
    name: str
    is_default: bool = False


class WarehouseRead(TimestampedRead):
    tenant_id: uuid.UUID
    location_id: uuid.UUID | None
    name: str
    is_default: bool


class StockItemRead(TimestampedRead):
    product_id: uuid.UUID
    warehouse_id: uuid.UUID
    qty: Decimal
    reserved_qty: Decimal
    min_stock: Decimal
    max_stock: Decimal | None


class StockMovementCreate(BaseSchema):
    product_id: uuid.UUID
    warehouse_id: uuid.UUID
    movement_type: str
    qty: Decimal
    reference_id: uuid.UUID | None = None
    reference_type: str | None = None
    device_id: uuid.UUID | None = None
    location_id: uuid.UUID | None = None
    note: str | None = None


class StockMovementRead(TimestampedRead):
    product_id: uuid.UUID
    warehouse_id: uuid.UUID
    movement_type: str
    qty: Decimal
    reference_id: uuid.UUID | None
    reference_type: str | None
    device_id: uuid.UUID | None
    location_id: uuid.UUID | None
    note: str | None
    occurred_at: datetime
