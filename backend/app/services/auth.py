import hashlib
import uuid
from datetime import datetime, timedelta, timezone

from jose import jwt
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.core.config import settings
from app.models.auth import Role, User
from app.schemas.auth import PinLoginResponse, RoleCreate, UserCreate


def _hash_pin(pin: str) -> str:
    return hashlib.sha256(pin.encode()).hexdigest()


def _create_token(user_id: uuid.UUID, permissions: list[str]) -> str:
    payload = {
        "sub": str(user_id),
        "permissions": permissions,
        "exp": datetime.now(timezone.utc) + timedelta(minutes=settings.access_token_expire_minutes),
    }
    return jwt.encode(payload, settings.secret_key, algorithm="HS256")


async def create_role(db: AsyncSession, data: RoleCreate) -> Role:
    obj = Role(**data.model_dump())
    db.add(obj)
    await db.commit()
    await db.refresh(obj)
    return obj


async def list_roles(db: AsyncSession, tenant_id: uuid.UUID) -> list[Role]:
    result = await db.execute(
        select(Role).where(Role.tenant_id == tenant_id, Role.deleted_at.is_(None))
    )
    return list(result.scalars().all())


async def create_user(db: AsyncSession, data: UserCreate) -> User:
    payload = data.model_dump(exclude={"pin"})
    # Ensure UUIDs in JSON list are serialised as strings
    payload["allowed_location_ids"] = [str(x) for x in payload.get("allowed_location_ids", [])]
    if data.pin:
        payload["pin_hash"] = _hash_pin(data.pin)
    obj = User(**payload)
    db.add(obj)
    await db.commit()
    await db.refresh(obj)
    return obj


async def get_user(db: AsyncSession, user_id: uuid.UUID) -> User | None:
    result = await db.execute(
        select(User)
        .where(User.id == user_id, User.deleted_at.is_(None))
        .options(selectinload(User.role))
    )
    return result.scalar_one_or_none()


async def list_users(db: AsyncSession, tenant_id: uuid.UUID) -> list[User]:
    result = await db.execute(
        select(User)
        .where(User.tenant_id == tenant_id, User.deleted_at.is_(None))
        .options(selectinload(User.role))
        .order_by(User.display_name)
    )
    return list(result.scalars().all())


async def pin_login(
    db: AsyncSession, location_id: uuid.UUID, pin: str
) -> PinLoginResponse | None:
    """Find active user by PIN for this location."""
    pin_hash = _hash_pin(pin)
    result = await db.execute(
        select(User)
        .where(
            User.pin_hash == pin_hash,
            User.is_active.is_(True),
            User.deleted_at.is_(None),
        )
        .options(selectinload(User.role))
    )
    user = result.scalar_one_or_none()
    if not user:
        return None
    # Check location access
    if user.allowed_location_ids and str(location_id) not in [
        str(x) for x in user.allowed_location_ids
    ]:
        return None
    permissions: list[str] = user.role.permissions if user.role else []
    token = _create_token(user.id, permissions)
    return PinLoginResponse(
        access_token=token,
        user_id=user.id,
        display_name=user.display_name,
        permissions=permissions,
    )
