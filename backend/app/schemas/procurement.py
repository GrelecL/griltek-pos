import uuid
from datetime import datetime
from decimal import Decimal

from app.schemas.base import BaseSchema, TimestampedRead


class SupplierCreate(BaseSchema):
    tenant_id: uuid.UUID
    name: str
    contact_name: str | None = None
    email: str | None = None
    phone: str | None = None
    address: str | None = None
    tax_id: str | None = None

class SupplierRead(TimestampedRead):
    tenant_id: uuid.UUID
    name: str
    contact_name: str | None
    email: str | None
    phone: str | None
    address: str | None
    tax_id: str | None
    is_active: bool

class SupplierUpdate(BaseSchema):
    name: str | None = None
    contact_name: str | None = None
    email: str | None = None
    phone: str | None = None
    address: str | None = None
    tax_id: str | None = None
    is_active: bool | None = None


class POLineCreate(BaseSchema):
    product_id: uuid.UUID
    qty_ordered: Decimal
    unit_cost: Decimal

class POLineRead(TimestampedRead):
    order_id: uuid.UUID
    product_id: uuid.UUID
    qty_ordered: Decimal
    qty_received: Decimal
    unit_cost: Decimal

class PurchaseOrderCreate(BaseSchema):
    tenant_id: uuid.UUID
    supplier_id: uuid.UUID
    warehouse_id: uuid.UUID
    order_number: str | None = None
    expected_at: datetime | None = None
    note: str | None = None
    lines: list[POLineCreate] = []

class PurchaseOrderRead(TimestampedRead):
    tenant_id: uuid.UUID
    supplier_id: uuid.UUID
    warehouse_id: uuid.UUID
    status: str
    order_number: str | None
    ordered_at: datetime | None
    expected_at: datetime | None
    note: str | None
    lines: list[POLineRead] = []


class GoodsReceiptLineCreate(BaseSchema):
    order_line_id: uuid.UUID
    product_id: uuid.UUID
    qty_received: Decimal
    unit_cost: Decimal

class GoodsReceiptLineRead(TimestampedRead):
    receipt_id: uuid.UUID
    order_line_id: uuid.UUID
    product_id: uuid.UUID
    qty_received: Decimal
    unit_cost: Decimal

class GoodsReceiptCreate(BaseSchema):
    order_id: uuid.UUID
    warehouse_id: uuid.UUID
    note: str | None = None
    lines: list[GoodsReceiptLineCreate] = []

class GoodsReceiptRead(TimestampedRead):
    order_id: uuid.UUID
    warehouse_id: uuid.UUID
    received_at: datetime
    note: str | None
    lines: list[GoodsReceiptLineRead] = []


class TransferLineCreate(BaseSchema):
    product_id: uuid.UUID
    qty: Decimal

class TransferLineRead(TimestampedRead):
    transfer_id: uuid.UUID
    product_id: uuid.UUID
    qty: Decimal

class TransferCreate(BaseSchema):
    tenant_id: uuid.UUID
    from_warehouse_id: uuid.UUID
    to_warehouse_id: uuid.UUID
    note: str | None = None
    lines: list[TransferLineCreate] = []

class TransferRead(TimestampedRead):
    tenant_id: uuid.UUID
    from_warehouse_id: uuid.UUID
    to_warehouse_id: uuid.UUID
    status: str
    transferred_at: datetime | None
    note: str | None
    lines: list[TransferLineRead] = []


class StockTakeLineInput(BaseSchema):
    product_id: uuid.UUID
    qty_counted: Decimal

class StockTakeLineRead(TimestampedRead):
    stock_take_id: uuid.UUID
    product_id: uuid.UUID
    qty_system: Decimal
    qty_counted: Decimal | None
    qty_difference: Decimal | None

class StockTakeCreate(BaseSchema):
    tenant_id: uuid.UUID
    warehouse_id: uuid.UUID
    note: str | None = None

class StockTakeRead(TimestampedRead):
    tenant_id: uuid.UUID
    warehouse_id: uuid.UUID
    status: str
    started_at: datetime
    completed_at: datetime | None
    note: str | None
    lines: list[StockTakeLineRead] = []
