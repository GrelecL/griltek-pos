import uuid

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.location import Location, LocationConfig
from app.models.tenant import Tenant
from app.schemas.tenant import LocationConfigUpdate, LocationCreate, TenantCreate


async def create_tenant(db: AsyncSession, data: TenantCreate) -> Tenant:
    obj = Tenant(**data.model_dump())
    db.add(obj)
    await db.commit()
    await db.refresh(obj)
    return obj


async def get_tenant(db: AsyncSession, tenant_id: uuid.UUID) -> Tenant | None:
    result = await db.execute(select(Tenant).where(Tenant.id == tenant_id, Tenant.deleted_at.is_(None)))
    return result.scalar_one_or_none()


async def list_tenants(db: AsyncSession) -> list[Tenant]:
    result = await db.execute(select(Tenant).where(Tenant.deleted_at.is_(None)).order_by(Tenant.name))
    return list(result.scalars().all())


async def create_location(db: AsyncSession, data: LocationCreate) -> Location:
    obj = Location(**data.model_dump())
    db.add(obj)
    await db.flush()  # get obj.id before creating config
    config = LocationConfig(location_id=obj.id)
    db.add(config)
    await db.commit()
    await db.refresh(obj)
    return obj


async def get_location(db: AsyncSession, location_id: uuid.UUID) -> Location | None:
    result = await db.execute(select(Location).where(Location.id == location_id, Location.deleted_at.is_(None)))
    return result.scalar_one_or_none()


async def list_locations(db: AsyncSession, tenant_id: uuid.UUID) -> list[Location]:
    result = await db.execute(
        select(Location)
        .where(Location.tenant_id == tenant_id, Location.deleted_at.is_(None))
        .order_by(Location.name)
    )
    return list(result.scalars().all())


async def get_location_config(db: AsyncSession, location_id: uuid.UUID) -> LocationConfig | None:
    result = await db.execute(select(LocationConfig).where(LocationConfig.location_id == location_id))
    return result.scalar_one_or_none()


async def update_location_config(db: AsyncSession, location_id: uuid.UUID, data: LocationConfigUpdate) -> LocationConfig | None:
    config = await get_location_config(db, location_id)
    if not config:
        return None
    for k, v in data.model_dump(exclude_none=True).items():
        setattr(config, k, v)
    config.version += 1
    await db.commit()
    await db.refresh(config)
    return config
