import uuid
from decimal import Decimal

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

import app.services.tenant as svc
from app.schemas.tenant import LocationConfigUpdate, LocationCreate, TenantCreate


@pytest.mark.asyncio
async def test_create_tenant(db: AsyncSession):
    tenant = await svc.create_tenant(db, TenantCreate(name="Acme Corp", slug="acme"))
    assert tenant.id is not None
    assert tenant.name == "Acme Corp"
    assert tenant.slug == "acme"


@pytest.mark.asyncio
async def test_get_tenant(db: AsyncSession):
    tenant = await svc.create_tenant(db, TenantCreate(name="GetMe", slug="getme"))
    fetched = await svc.get_tenant(db, tenant.id)
    assert fetched is not None
    assert fetched.id == tenant.id


@pytest.mark.asyncio
async def test_list_tenants(db: AsyncSession):
    await svc.create_tenant(db, TenantCreate(name="T1", slug="t1"))
    await svc.create_tenant(db, TenantCreate(name="T2", slug="t2"))
    tenants = await svc.list_tenants(db)
    assert len(tenants) >= 2


@pytest.mark.asyncio
async def test_get_nonexistent_tenant(db: AsyncSession):
    result = await svc.get_tenant(db, uuid.uuid4())
    assert result is None


@pytest.mark.asyncio
async def test_create_location_auto_creates_config(db: AsyncSession):
    tenant = await svc.create_tenant(db, TenantCreate(name="Loc Tenant", slug="loc-tenant"))
    location = await svc.create_location(db, LocationCreate(
        tenant_id=tenant.id, name="Main Store", address="123 Main St",
    ))
    assert location.id is not None
    assert location.name == "Main Store"

    config = await svc.get_location_config(db, location.id)
    assert config is not None
    assert config.location_id == location.id
    # defaults
    assert config.self_checkout is False
    assert config.currency == "EUR"


@pytest.mark.asyncio
async def test_list_locations(db: AsyncSession):
    tenant = await svc.create_tenant(db, TenantCreate(name="Multi Loc", slug="multi-loc"))
    await svc.create_location(db, LocationCreate(tenant_id=tenant.id, name="Store A"))
    await svc.create_location(db, LocationCreate(tenant_id=tenant.id, name="Store B"))
    locs = await svc.list_locations(db, tenant.id)
    assert len(locs) == 2


@pytest.mark.asyncio
async def test_update_location_config(db: AsyncSession):
    tenant = await svc.create_tenant(db, TenantCreate(name="Cfg Tenant", slug="cfg-tenant"))
    location = await svc.create_location(db, LocationCreate(tenant_id=tenant.id, name="Feature Store"))

    updated = await svc.update_location_config(db, location.id, LocationConfigUpdate(
        self_checkout=True,
        tables=True,
        tips=True,
        vat_eat_in=Decimal("5.0"),
        currency="USD",
    ))
    assert updated is not None
    assert updated.self_checkout is True
    assert updated.tables is True
    assert updated.tips is True
    assert updated.vat_eat_in == Decimal("5.0")
    assert updated.currency == "USD"
    assert updated.version == 2


@pytest.mark.asyncio
async def test_update_nonexistent_config(db: AsyncSession):
    result = await svc.update_location_config(db, uuid.uuid4(), LocationConfigUpdate(self_checkout=True))
    assert result is None


@pytest.mark.asyncio
async def test_location_different_business_types(db: AsyncSession):
    tenant = await svc.create_tenant(db, TenantCreate(name="BT Tenant", slug="bt-tenant"))
    retail = await svc.create_location(db, LocationCreate(
        tenant_id=tenant.id, name="Retail", business_type="retail",
    ))
    hosp = await svc.create_location(db, LocationCreate(
        tenant_id=tenant.id, name="Restaurant", business_type="hospitality",
    ))
    assert retail.business_type == "retail"
    assert hosp.business_type == "hospitality"
