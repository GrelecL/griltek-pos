"""Sync event types shared between backend (cloud) and store-server (edge)."""
import uuid
from datetime import datetime
from enum import StrEnum
from pydantic import BaseModel, Field


class SyncDirection(StrEnum):
    PULL = "pull"   # cloud → edge
    PUSH = "push"   # edge → cloud


class SyncEventType(StrEnum):
    PRODUCT = "product"
    PRICE = "price"
    BARCODE = "barcode"
    CATEGORY = "category"
    PROMOTION = "promotion"
    STOCK_MOVEMENT = "stock_movement"
    SALE = "sale"
    PAYMENT = "payment"
    FISCAL_RECORD = "fiscal_record"
    CASH_SESSION = "cash_session"


class SyncEvent(BaseModel):
    event_id: uuid.UUID = Field(default_factory=uuid.uuid4)
    event_type: SyncEventType
    payload: dict
    device_id: uuid.UUID
    location_id: uuid.UUID
    occurred_at: datetime = Field(default_factory=datetime.utcnow)
    version: int = 1


class SyncCursor(BaseModel):
    location_id: uuid.UUID
    pull_version: int = 0    # last pulled version from cloud
    push_ts: datetime | None = None  # last pushed event timestamp
