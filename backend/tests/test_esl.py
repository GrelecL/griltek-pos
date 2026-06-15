"""Tests for ESL device management and sync."""
import uuid
from decimal import Decimal

import pytest

from app.adapters.esl.adapter import MockESLAdapter, get_esl_adapter
from app.models.catalog import Price, Product
from app.models.esl import ESLDevice
from app.models.location import Location, LocationConfig
from app.models.tenant import Tenant
from app.services import esl as esl_svc


async def _setup(db):
    tenant = Tenant(id=uuid.uuid4(), name="T", slug="t-esl")
    db.add(tenant)
    await db.flush()
    loc = Location(id=uuid.uuid4(), tenant_id=tenant.id, name="L", address="A",
                   business_type="retail", timezone="UTC")
    db.add(loc)
    await db.flush()
    db.add(LocationConfig(id=uuid.uuid4(), location_id=loc.id))
    product = Product(
        id=uuid.uuid4(), tenant_id=tenant.id,
        plu="ESL-01", name="Mleko 1L",
        vat_rate=Decimal("9.5"), unit="piece",
        is_weighable=False, age_restricted=False, allergens=[], is_active=True,
    )
    db.add(product)
    db.add(Price(
        id=uuid.uuid4(), product_id=product.id,
        price_type="regular", amount=Decimal("1.29"),
        min_qty=1, is_active=True,
    ))
    await db.flush()
    return tenant, loc, product


# ── adapter ───────────────────────────────────────────────────────────────────

def test_mock_adapter_returns_mock():
    adapter = get_esl_adapter()
    assert isinstance(adapter, MockESLAdapter)


# ── device management ─────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_register_device(db):
    tenant, loc, product = await _setup(db)
    device = await esl_svc.register_device(db, loc.id, "ESL-UNIT-001")
    await db.commit()
    assert device.esl_id == "ESL-UNIT-001"
    assert device.status == "pending"
    assert device.product_id is None


@pytest.mark.asyncio
async def test_register_device_with_product(db):
    tenant, loc, product = await _setup(db)
    device = await esl_svc.register_device(db, loc.id, "ESL-UNIT-002", product_id=product.id)
    await db.commit()
    assert device.product_id == product.id


@pytest.mark.asyncio
async def test_assign_product(db):
    tenant, loc, product = await _setup(db)
    device = await esl_svc.register_device(db, loc.id, "ESL-UNIT-003")
    await db.flush()
    await esl_svc.assign_product(db, device.id, product.id)
    await db.commit()
    await db.refresh(device)
    assert device.product_id == product.id
    assert device.status == "pending"


@pytest.mark.asyncio
async def test_list_devices(db):
    tenant, loc, product = await _setup(db)
    await esl_svc.register_device(db, loc.id, "ESL-A")
    await esl_svc.register_device(db, loc.id, "ESL-B")
    await db.commit()
    devices = await esl_svc.list_devices(db, loc.id)
    assert len(devices) == 2


# ── sync ──────────────────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_sync_device_sets_synced(db):
    tenant, loc, product = await _setup(db)
    device = await esl_svc.register_device(db, loc.id, "ESL-SYNC-01", product_id=product.id)
    await db.flush()

    await esl_svc.sync_device(db, device.id, tenant.id)
    await db.commit()
    await db.refresh(device)

    assert device.status == "synced"
    assert device.last_price == Decimal("1.29")
    assert device.last_synced_at is not None
    assert device.last_error is None


@pytest.mark.asyncio
async def test_sync_device_records_label_in_adapter(db):
    tenant, loc, product = await _setup(db)
    device = await esl_svc.register_device(db, loc.id, "ESL-SYNC-02", product_id=product.id)
    await db.flush()

    adapter = get_esl_adapter()
    adapter.pushed.clear()

    await esl_svc.sync_device(db, device.id, tenant.id)
    await db.commit()

    assert len(adapter.pushed) >= 1
    label = adapter.pushed[-1]
    assert label.plu == "ESL-01"
    assert label.price == Decimal("1.29")
    assert label.original_price is None  # no promo active


@pytest.mark.asyncio
async def test_sync_device_no_product_raises(db):
    tenant, loc, product = await _setup(db)
    device = await esl_svc.register_device(db, loc.id, "ESL-NOPROD")
    await db.flush()
    with pytest.raises(ValueError, match="no linked product"):
        await esl_svc.sync_device(db, device.id, tenant.id)


@pytest.mark.asyncio
async def test_sync_device_no_price_sets_error(db):
    tenant, loc, product = await _setup(db)
    # product without a Price row
    no_price_product = Product(
        id=uuid.uuid4(), tenant_id=tenant.id,
        plu="NOPRICE", name="Ghost Product",
        vat_rate=Decimal("22"), unit="piece",
        is_weighable=False, age_restricted=False, allergens=[], is_active=True,
    )
    db.add(no_price_product)
    await db.flush()
    device = await esl_svc.register_device(db, loc.id, "ESL-NOPRICE", product_id=no_price_product.id)
    await db.flush()

    await esl_svc.sync_device(db, device.id, tenant.id)
    await db.commit()
    await db.refresh(device)

    assert device.status == "error"
    assert device.last_error is not None


@pytest.mark.asyncio
async def test_sync_location_summary(db):
    tenant, loc, product = await _setup(db)
    await esl_svc.register_device(db, loc.id, "ESL-LOC-01", product_id=product.id)
    await esl_svc.register_device(db, loc.id, "ESL-LOC-02", product_id=product.id)
    await esl_svc.register_device(db, loc.id, "ESL-LOC-SKIP")  # no product
    await db.flush()

    summary = await esl_svc.sync_location(db, loc.id, tenant.id)
    await db.commit()

    assert summary["synced"] == 2
    assert summary["skipped"] == 1
    assert summary["errors"] == 0
    assert summary["total"] == 3
