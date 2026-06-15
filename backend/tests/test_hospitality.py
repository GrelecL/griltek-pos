"""Tests for hospitality service: tables, orders, KDS, materialise."""
import uuid
from decimal import Decimal

import pytest
from sqlalchemy import select

from app.models.auth import Role, User
from app.models.hospitality import Order, OrderLine, Table
from app.models.location import Location, LocationConfig
from app.models.pos import CashSession, Sale
from app.models.tenant import Tenant
from app.services.hospitality import (
    FloorAreaCreate,
    OrderCreate,
    OrderLineCreate,
    TableCreate,
    add_order_lines,
    create_floor_area,
    create_order,
    create_table,
    fire_course,
    get_kds_lines,
    get_order,
    list_open_orders,
    materialise_order,
    set_table_status,
    update_kds_status,
)

# ── fixtures ──────────────────────────────────────────────────────────────────

async def _make_location(db) -> Location:
    tid = uuid.uuid4()
    tenant = Tenant(id=tid, name="T", slug="t")
    db.add(tenant)
    await db.flush()
    loc = Location(id=uuid.uuid4(), tenant_id=tid, name="L", address="A", business_type="hospitality", timezone="UTC")
    db.add(loc)
    await db.flush()
    cfg = LocationConfig(id=uuid.uuid4(), location_id=loc.id)
    db.add(cfg)
    await db.flush()
    return loc


async def _make_user(db, tenant_id) -> User:
    role = Role(id=uuid.uuid4(), tenant_id=tenant_id, name="staff", permissions=[])
    db.add(role)
    await db.flush()
    user = User(id=uuid.uuid4(), tenant_id=tenant_id, role_id=role.id, username="u", display_name="U", pin_hash="x")
    db.add(user)
    await db.flush()
    return user


def _line_data(product_id=None) -> OrderLineCreate:
    return OrderLineCreate(
        product_id=product_id or uuid.uuid4(),
        product_name="Pivo",
        plu="500",
        qty=Decimal("2"),
        unit_price=Decimal("3.50"),
        vat_rate=Decimal("0.22"),
        course=1,
        kds_station="bar",
    )


# ── tests ─────────────────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_create_floor_area_and_table(db):
    loc = await _make_location(db)
    area = await create_floor_area(db, FloorAreaCreate(location_id=loc.id, name="Terasa"))
    await db.flush()
    table = await create_table(db, TableCreate(floor_area_id=area.id, number="T1", capacity=4))
    await db.commit()

    result = await db.execute(select(Table).where(Table.id == table.id))
    t = result.scalar_one()
    assert t.number == "T1"
    assert t.status == "free"


@pytest.mark.asyncio
async def test_set_table_status(db):
    loc = await _make_location(db)
    area = await create_floor_area(db, FloorAreaCreate(location_id=loc.id, name="Sala"))
    await db.flush()
    table = await create_table(db, TableCreate(floor_area_id=area.id, number="S1"))
    await db.commit()

    await set_table_status(db, table.id, "occupied")
    await db.commit()
    await db.refresh(table)
    assert table.status == "occupied"


@pytest.mark.asyncio
async def test_create_order_sets_table_occupied(db):
    loc = await _make_location(db)
    user = await _make_user(db, loc.tenant_id)
    area = await create_floor_area(db, FloorAreaCreate(location_id=loc.id, name="A"))
    await db.flush()
    table = await create_table(db, TableCreate(floor_area_id=area.id, number="1"))
    await db.commit()

    order = await create_order(db, OrderCreate(
        location_id=loc.id, table_id=table.id, user_id=user.id,
        lines=[_line_data()],
    ))
    await db.commit()

    await db.refresh(table)
    assert table.status == "occupied"
    assert order.status == "open"


@pytest.mark.asyncio
async def test_add_order_lines(db):
    loc = await _make_location(db)
    user = await _make_user(db, loc.tenant_id)
    await db.commit()

    order = await create_order(db, OrderCreate(location_id=loc.id, user_id=user.id, lines=[_line_data()]))
    await db.commit()

    await add_order_lines(db, order.id, [_line_data()])
    await db.commit()

    result = await db.execute(select(OrderLine).where(OrderLine.order_id == order.id))
    assert len(result.scalars().all()) == 2


@pytest.mark.asyncio
async def test_fire_course_changes_kds_status(db):
    loc = await _make_location(db)
    user = await _make_user(db, loc.tenant_id)

    ld = _line_data()
    ld.course = 1
    order = await create_order(db, OrderCreate(location_id=loc.id, user_id=user.id, lines=[ld]))
    await db.commit()

    fired = await fire_course(db, order.id, course=1)
    await db.commit()
    assert fired == 1

    fetched = await get_order(db, order.id)
    assert fetched.lines[0].kds_status == "in_kitchen"
    assert fetched.lines[0].fired_at is not None


@pytest.mark.asyncio
async def test_update_kds_status_ready(db):
    loc = await _make_location(db)
    user = await _make_user(db, loc.tenant_id)

    order = await create_order(db, OrderCreate(location_id=loc.id, user_id=user.id, lines=[_line_data()]))
    await db.commit()

    loaded = await get_order(db, order.id)
    line_id = loaded.lines[0].id
    await fire_course(db, order.id, course=1)
    await update_kds_status(db, line_id, "ready")
    await db.commit()

    result = await db.execute(select(OrderLine).where(OrderLine.id == line_id))
    line = result.scalar_one()
    assert line.kds_status == "ready"
    assert line.ready_at is not None


@pytest.mark.asyncio
async def test_get_kds_lines_filters_by_station(db):
    loc = await _make_location(db)
    user = await _make_user(db, loc.tenant_id)

    bar_line = _line_data(); bar_line.kds_station = "bar"; bar_line.course = 1
    grill_line = _line_data(); grill_line.kds_station = "grill"; grill_line.course = 1

    order = await create_order(db, OrderCreate(
        location_id=loc.id, user_id=user.id, lines=[bar_line, grill_line],
    ))
    await db.commit()
    await fire_course(db, order.id, 1)
    await db.commit()

    bar_lines = await get_kds_lines(db, loc.id, station="bar")
    assert len(bar_lines) == 1
    assert bar_lines[0].kds_station == "bar"

    all_lines = await get_kds_lines(db, loc.id)
    assert len(all_lines) == 2


@pytest.mark.asyncio
async def test_materialise_order_creates_sale(db):
    loc = await _make_location(db)
    user = await _make_user(db, loc.tenant_id)

    # create cash session
    session = CashSession(
        id=uuid.uuid4(), location_id=loc.id, user_id=user.id,
        status="open", opening_float=Decimal("50"),
    )
    db.add(session)
    await db.flush()

    order = await create_order(db, OrderCreate(
        location_id=loc.id, user_id=user.id,
        lines=[_line_data()],
    ))
    await db.commit()

    sale = await materialise_order(
        db, order.id, session.id, user.id,
        payments=[{"method": "cash", "amount": "7.00"}],
    )
    await db.commit()

    result = await db.execute(select(Sale).where(Sale.id == sale.id))
    s = result.scalar_one()
    assert s.total == Decimal("7.00")

    result2 = await db.execute(select(Order).where(Order.id == order.id))
    o = result2.scalar_one()
    assert o.status == "closed"
    assert o.sale_id == sale.id


@pytest.mark.asyncio
async def test_list_open_orders(db):
    loc = await _make_location(db)
    user = await _make_user(db, loc.tenant_id)

    await create_order(db, OrderCreate(location_id=loc.id, user_id=user.id))
    await create_order(db, OrderCreate(location_id=loc.id, user_id=user.id))
    await db.commit()

    orders = await list_open_orders(db, loc.id)
    assert len(orders) == 2
