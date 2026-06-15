import uuid
from decimal import Decimal

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

import app.services.catalog as catalog_svc
import app.services.tenant as tenant_svc
import app.services.warehouse as svc
from app.schemas.catalog import ProductCreate
from app.schemas.tenant import TenantCreate
from app.schemas.warehouse import StockMovementCreate, WarehouseCreate


async def make_tenant(db: AsyncSession) -> uuid.UUID:
    t = await tenant_svc.create_tenant(db, TenantCreate(name="WH Tenant", slug=f"wh-{uuid.uuid4().hex[:6]}"))
    return t.id


async def make_product(db: AsyncSession, tenant_id: uuid.UUID, plu: str = "P1") -> uuid.UUID:
    p = await catalog_svc.create_product(db, ProductCreate(tenant_id=tenant_id, plu=plu, name=f"Prod {plu}"))
    return p.id


async def make_warehouse(db: AsyncSession, tenant_id: uuid.UUID, name: str = "Main") -> uuid.UUID:
    w = await svc.create_warehouse(db, WarehouseCreate(tenant_id=tenant_id, name=name))
    return w.id


@pytest.mark.asyncio
async def test_create_warehouse(db: AsyncSession):
    tid = await make_tenant(db)
    wh = await svc.create_warehouse(db, WarehouseCreate(tenant_id=tid, name="Main WH"))
    assert wh.id is not None
    assert wh.name == "Main WH"


@pytest.mark.asyncio
async def test_get_warehouse(db: AsyncSession):
    tid = await make_tenant(db)
    wh = await svc.create_warehouse(db, WarehouseCreate(tenant_id=tid, name="WH1"))
    fetched = await svc.get_warehouse(db, wh.id)
    assert fetched is not None
    assert fetched.id == wh.id


@pytest.mark.asyncio
async def test_list_warehouses(db: AsyncSession):
    tid = await make_tenant(db)
    await svc.create_warehouse(db, WarehouseCreate(tenant_id=tid, name="WH A"))
    await svc.create_warehouse(db, WarehouseCreate(tenant_id=tid, name="WH B"))
    whs = await svc.list_warehouses(db, tid)
    assert len(whs) == 2


@pytest.mark.asyncio
async def test_movement_creates_stock_item(db: AsyncSession):
    tid = await make_tenant(db)
    pid = await make_product(db, tid, "M1")
    wid = await make_warehouse(db, tid)

    movement = await svc.create_movement(db, StockMovementCreate(
        product_id=pid, warehouse_id=wid, movement_type="receipt", qty=Decimal("10.000"),
    ))
    assert movement.id is not None

    stock = await svc.get_stock_item(db, pid, wid)
    assert stock is not None
    assert stock.qty == Decimal("10.000")


@pytest.mark.asyncio
async def test_multiple_movements_accumulate(db: AsyncSession):
    tid = await make_tenant(db)
    pid = await make_product(db, tid, "M2")
    wid = await make_warehouse(db, tid)

    await svc.create_movement(db, StockMovementCreate(
        product_id=pid, warehouse_id=wid, movement_type="receipt", qty=Decimal("20.000"),
    ))
    await svc.create_movement(db, StockMovementCreate(
        product_id=pid, warehouse_id=wid, movement_type="sale", qty=Decimal("-5.000"),
    ))
    await svc.create_movement(db, StockMovementCreate(
        product_id=pid, warehouse_id=wid, movement_type="receipt", qty=Decimal("3.000"),
    ))

    stock = await svc.get_stock_item(db, pid, wid)
    assert stock.qty == Decimal("18.000")
    assert stock.version == 3


@pytest.mark.asyncio
async def test_list_movements_by_product(db: AsyncSession):
    tid = await make_tenant(db)
    pid1 = await make_product(db, tid, "LM1")
    pid2 = await make_product(db, tid, "LM2")
    wid = await make_warehouse(db, tid)

    await svc.create_movement(db, StockMovementCreate(
        product_id=pid1, warehouse_id=wid, movement_type="receipt", qty=Decimal("5"),
    ))
    await svc.create_movement(db, StockMovementCreate(
        product_id=pid2, warehouse_id=wid, movement_type="receipt", qty=Decimal("3"),
    ))
    await svc.create_movement(db, StockMovementCreate(
        product_id=pid1, warehouse_id=wid, movement_type="sale", qty=Decimal("-1"),
    ))

    movements_p1 = await svc.list_movements(db, product_id=pid1)
    assert len(movements_p1) == 2

    movements_p2 = await svc.list_movements(db, product_id=pid2)
    assert len(movements_p2) == 1


@pytest.mark.asyncio
async def test_list_movements_by_warehouse(db: AsyncSession):
    tid = await make_tenant(db)
    pid = await make_product(db, tid, "LMW")
    wid1 = await make_warehouse(db, tid, "WH1")
    wid2 = await make_warehouse(db, tid, "WH2")

    await svc.create_movement(db, StockMovementCreate(
        product_id=pid, warehouse_id=wid1, movement_type="receipt", qty=Decimal("10"),
    ))
    await svc.create_movement(db, StockMovementCreate(
        product_id=pid, warehouse_id=wid2, movement_type="receipt", qty=Decimal("5"),
    ))

    movements_wh1 = await svc.list_movements(db, warehouse_id=wid1)
    assert len(movements_wh1) == 1

    all_movements = await svc.list_movements(db)
    assert len(all_movements) == 2


@pytest.mark.asyncio
async def test_list_stock_by_warehouse(db: AsyncSession):
    tid = await make_tenant(db)
    pid1 = await make_product(db, tid, "ST1")
    pid2 = await make_product(db, tid, "ST2")
    wid = await make_warehouse(db, tid)

    await svc.create_movement(db, StockMovementCreate(
        product_id=pid1, warehouse_id=wid, movement_type="receipt", qty=Decimal("10"),
    ))
    await svc.create_movement(db, StockMovementCreate(
        product_id=pid2, warehouse_id=wid, movement_type="receipt", qty=Decimal("20"),
    ))

    stock = await svc.list_stock(db, warehouse_id=wid)
    assert len(stock) == 2
