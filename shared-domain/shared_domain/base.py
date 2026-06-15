import uuid
from datetime import datetime
from pydantic import BaseModel, Field


class BaseSchema(BaseModel):
    model_config = {"from_attributes": True}


class TimestampedSchema(BaseSchema):
    id: uuid.UUID = Field(default_factory=uuid.uuid4)
    created_at: datetime
    updated_at: datetime
    deleted_at: datetime | None = None
    version: int = 1
