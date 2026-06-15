import uuid

from app.schemas.base import BaseSchema, TimestampedRead


class RoleCreate(BaseSchema):
    tenant_id: uuid.UUID
    name: str
    permissions: list[str] = []


class RoleRead(TimestampedRead):
    tenant_id: uuid.UUID
    name: str
    permissions: list


class UserCreate(BaseSchema):
    tenant_id: uuid.UUID
    role_id: uuid.UUID
    username: str
    display_name: str
    pin: str | None = None
    email: str | None = None
    allowed_location_ids: list[uuid.UUID] = []


class UserRead(TimestampedRead):
    tenant_id: uuid.UUID
    role_id: uuid.UUID
    username: str
    display_name: str
    email: str | None
    is_active: bool
    allowed_location_ids: list


class PinLoginRequest(BaseSchema):
    location_id: uuid.UUID
    device_id: uuid.UUID | None = None
    pin: str


class PinLoginResponse(BaseSchema):
    access_token: str
    token_type: str = "bearer"
    user_id: uuid.UUID
    display_name: str
    permissions: list[str]
