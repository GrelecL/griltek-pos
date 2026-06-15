"""Tests for Step 3: POS core, RBAC, CashSession, Customer."""
import uuid
from decimal import Decimal

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

import app.services.auth as auth_svc
import app.services.catalog as catalog_svc
import app.services.customer as customer_svc
import app.services.pos as pos_svc
import app.services.tenant as tenant_svc
import app.services.warehouse as warehouse_svc
from app.models.location import Location
from app.schemas.auth import RoleCreate, UserCreate
from app.schemas.catalog import ProductCreate
from app.schemas.customer import CreditAccountCreate, CustomerCreate, CustomerUpdate
from app.schemas.pos import (
    CashAdjustment,
    CashSessionClose,
    CashSessionOpen,
    PaymentCreate,
    SaleCreate,
    SaleLineCreate,
)
from app.schemas.tenant import TenantCreate
from app.schemas.warehouse import WarehouseCreate

# ── Seed helpers ──────────────────────────────────────────────────────────────

async def make_tenant(db: AsyncSession) -> uuid.UUID:
    t = await tenant_svc.create_tenant(
        db, TenantCreate(name="POS Tenant", slug=f"pos-{uuid.uuid4().hex[:6]}")
    )
    return t.id


async def make_location(db: AsyncSession, tenant_id: uuid.UUID) -> uuid.UUID:
    loc = Location(tenant_id=tenant_id, name="Main Store")
    db.add(loc)
    await db.commit()
    await db.refresh(loc)
    return loc.id


async def make_warehouse(db: AsyncSession, tenant_id: uuid.UUID, location_id: uuid.UUID) -> uuid.UUID:
    wh = await warehouse_svc.create_warehouse(
        db,
        WarehouseCreate(tenant_id=tenant_id, name="Main WH", location_id=location_id, is_default=True),
    )
    return wh.id


async def make_role(db: AsyncSession, tenant_id: uuid.UUID, perms: list[str] | None = None) -> uuid.UUID:
    role = await auth_svc.create_role(
        db,
        RoleCreate(
            tenant_id=tenant_id,
            name="cashier",
            permissions=perms or ["sale.create", "drawer.open"],
        ),
    )
    return role.id


async def make_user(
    db: AsyncSession,
    tenant_id: uuid.UUID,
    role_id: uuid.UUID,
    pin: str = "1234",
    allowed_location_ids: list[uuid.UUID] | None = None,
) -> uuid.UUID:
    user = await auth_svc.create_user(
        db,
        UserCreate(
            tenant_id=tenant_id,
            role_id=role_id,
            username=f"cashier_{uuid.uuid4().hex[:4]}",
            display_name="Test Cashier",
            pin=pin,
            allowed_location_ids=allowed_location_ids or [],
        ),
    )
    return user.id


async def make_product(db: AsyncSession, tenant_id: uuid.UUID) -> uuid.UUID:
    p = await catalog_svc.create_product(
        db,
        ProductCreate(
            tenant_id=tenant_id,
            plu=f"P{uuid.uuid4().hex[:4]}",
            name="Test Product",
        ),
    )
    return p.id


def make_sale_line(product_id: uuid.UUID) -> SaleLineCreate:
    return SaleLineCreate(
        product_id=product_id,
        product_name="Test Product",
        plu="P001",
        qty=Decimal("2"),
        unit_price=Decimal("10.00"),
        vat_rate=Decimal("9.5"),
    )


# ── RBAC / Auth tests ─────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_pin_login_success(db: AsyncSession):
    tid = await make_tenant(db)
    loc_id = await make_location(db, tid)
    role_id = await make_role(db, tid, ["sale.create"])
    await make_user(db, tid, role_id, pin="9999")

    result = await auth_svc.pin_login(db, loc_id, "9999")
    assert result is not None
    assert result.access_token != ""
    assert result.display_name == "Test Cashier"
    assert "sale.create" in result.permissions


@pytest.mark.asyncio
async def test_pin_login_wrong_pin(db: AsyncSession):
    tid = await make_tenant(db)
    loc_id = await make_location(db, tid)
    role_id = await make_role(db, tid)
    await make_user(db, tid, role_id, pin="1111")

    result = await auth_svc.pin_login(db, loc_id, "9999")
    assert result is None


@pytest.mark.asyncio
async def test_pin_login_location_restriction(db: AsyncSession):
    tid = await make_tenant(db)
    loc_id = await make_location(db, tid)
    other_loc_id = await make_location(db, tid)
    role_id = await make_role(db, tid)
    # User is restricted to other_loc_id only
    await make_user(db, tid, role_id, pin="4321", allowed_location_ids=[other_loc_id])

    # Try to login at loc_id — should fail
    result = await auth_svc.pin_login(db, loc_id, "4321")
    assert result is None

    # Login at the allowed location — should succeed
    result2 = await auth_svc.pin_login(db, other_loc_id, "4321")
    assert result2 is not None


# ── Customer tests ────────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_create_customer(db: AsyncSession):
    tid = await make_tenant(db)
    c = await customer_svc.create_customer(
        db, CustomerCreate(tenant_id=tid, name="ACME Corp", is_b2b=True, tax_id="SI12345678")
    )
    assert c.id is not None
    assert c.name == "ACME Corp"
    assert c.is_b2b is True
    assert c.tax_id == "SI12345678"


@pytest.mark.asyncio
async def test_update_customer(db: AsyncSession):
    tid = await make_tenant(db)
    c = await customer_svc.create_customer(
        db, CustomerCreate(tenant_id=tid, name="Old Name")
    )
    updated = await customer_svc.update_customer(
        db, c.id, CustomerUpdate(name="New Name", email="new@example.com")
    )
    assert updated is not None
    assert updated.name == "New Name"
    assert updated.email == "new@example.com"
    assert updated.version == 2


@pytest.mark.asyncio
async def test_credit_account(db: AsyncSession):
    tid = await make_tenant(db)
    c = await customer_svc.create_customer(
        db, CustomerCreate(tenant_id=tid, name="Credit Customer")
    )
    ca = await customer_svc.create_credit_account(
        db, CreditAccountCreate(customer_id=c.id, credit_limit=Decimal("500.00"))
    )
    assert ca.id is not None
    assert ca.credit_limit == Decimal("500.00")
    assert ca.balance == Decimal("0.00")

    fetched = await customer_svc.get_credit_account(db, c.id)
    assert fetched is not None
    assert fetched.id == ca.id


# ── CashSession tests ─────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_open_and_close_session(db: AsyncSession):
    tid = await make_tenant(db)
    loc_id = await make_location(db, tid)
    role_id = await make_role(db, tid)
    user_id = await make_user(db, tid, role_id)

    session = await pos_svc.open_session(
        db,
        CashSessionOpen(location_id=loc_id, user_id=user_id, opening_float=Decimal("100.00")),
    )
    assert session.status == "open"
    assert session.opening_float == Decimal("100.00")

    # cash_in adjustment
    session = await pos_svc.cash_in(
        db, session.id, CashAdjustment(amount=Decimal("50.00"))
    )
    assert session.cash_in == Decimal("50.00")

    # cash_out adjustment
    session = await pos_svc.cash_out(
        db, session.id, CashAdjustment(amount=Decimal("20.00"))
    )
    assert session.cash_out == Decimal("20.00")

    # close
    closed = await pos_svc.close_session(
        db, session.id, CashSessionClose(closing_float=Decimal("130.00"), note="End of day")
    )
    assert closed.status == "closed"
    assert closed.closing_float == Decimal("130.00")
    assert closed.closed_at is not None


@pytest.mark.asyncio
async def test_x_report(db: AsyncSession):
    tid = await make_tenant(db)
    loc_id = await make_location(db, tid)
    await make_warehouse(db, tid, loc_id)
    role_id = await make_role(db, tid)
    user_id = await make_user(db, tid, role_id)
    product_id = await make_product(db, tid)

    session = await pos_svc.open_session(
        db,
        CashSessionOpen(location_id=loc_id, user_id=user_id, opening_float=Decimal("100.00")),
    )

    await pos_svc.create_sale(
        db,
        SaleCreate(
            transaction_uuid=uuid.uuid4(),
            cash_session_id=session.id,
            location_id=loc_id,
            user_id=user_id,
            lines=[make_sale_line(product_id)],
            payments=[PaymentCreate(method="cash", amount=Decimal("20.00"))],
        ),
    )

    report = await pos_svc.x_report(db, session.id)
    assert report is not None
    assert report.sale_count == 1
    assert report.total_sales > Decimal("0")
    assert report.cash_sales == Decimal("20.00")
    # expected_cash = opening_float + cash_sales + cash_in - cash_out
    # cash_in on session also includes cash from create_sale, so session.cash_in = 20.00
    assert report.expected_cash == Decimal("100.00") + report.cash_sales + session.cash_in - session.cash_out


@pytest.mark.asyncio
async def test_z_report_requires_closed_session(db: AsyncSession):
    tid = await make_tenant(db)
    loc_id = await make_location(db, tid)
    role_id = await make_role(db, tid)
    user_id = await make_user(db, tid, role_id)

    session = await pos_svc.open_session(
        db,
        CashSessionOpen(location_id=loc_id, user_id=user_id),
    )

    # Z-report on open session should return None
    report = await pos_svc.z_report(db, session.id)
    assert report is None

    # Close and retry
    await pos_svc.close_session(
        db, session.id, CashSessionClose(closing_float=Decimal("0"))
    )
    report = await pos_svc.z_report(db, session.id)
    assert report is not None
    assert report.closed_at is not None


# ── Sale tests ────────────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_create_sale_computes_totals(db: AsyncSession):
    tid = await make_tenant(db)
    loc_id = await make_location(db, tid)
    await make_warehouse(db, tid, loc_id)
    role_id = await make_role(db, tid)
    user_id = await make_user(db, tid, role_id)
    product_id = await make_product(db, tid)

    session = await pos_svc.open_session(
        db, CashSessionOpen(location_id=loc_id, user_id=user_id)
    )

    # 2 units @ 10.00, VAT 9.5%, no discount
    # subtotal = 20.00
    # vat_amount = 20 * 9.5 / (100 + 9.5) = 1.7352...
    # total = 20.00
    sale = await pos_svc.create_sale(
        db,
        SaleCreate(
            transaction_uuid=uuid.uuid4(),
            cash_session_id=session.id,
            location_id=loc_id,
            user_id=user_id,
            lines=[
                SaleLineCreate(
                    product_id=product_id,
                    product_name="Widget",
                    plu="W1",
                    qty=Decimal("2"),
                    unit_price=Decimal("10.00"),
                    vat_rate=Decimal("9.5"),
                )
            ],
            payments=[PaymentCreate(method="card", amount=Decimal("20.00"))],
        ),
    )

    assert sale.subtotal == Decimal("20.00")
    assert sale.discount_total == Decimal("0.00")
    assert sale.total == Decimal("20.00")
    assert sale.vat_total > Decimal("0")
    assert len(sale.lines) == 1
    assert len(sale.payments) == 1
    assert sale.lines[0].line_total == Decimal("20.00")


@pytest.mark.asyncio
async def test_sale_idempotency(db: AsyncSession):
    tid = await make_tenant(db)
    loc_id = await make_location(db, tid)
    await make_warehouse(db, tid, loc_id)
    role_id = await make_role(db, tid)
    user_id = await make_user(db, tid, role_id)
    product_id = await make_product(db, tid)

    session = await pos_svc.open_session(
        db, CashSessionOpen(location_id=loc_id, user_id=user_id)
    )

    tx_uuid = uuid.uuid4()
    sale_data = SaleCreate(
        transaction_uuid=tx_uuid,
        cash_session_id=session.id,
        location_id=loc_id,
        user_id=user_id,
        lines=[make_sale_line(product_id)],
        payments=[PaymentCreate(method="cash", amount=Decimal("20.00"))],
    )

    sale1 = await pos_svc.create_sale(db, sale_data)
    sale2 = await pos_svc.create_sale(db, sale_data)

    assert sale1.id == sale2.id
    assert sale1.transaction_uuid == sale2.transaction_uuid


@pytest.mark.asyncio
async def test_void_sale(db: AsyncSession):
    tid = await make_tenant(db)
    loc_id = await make_location(db, tid)
    await make_warehouse(db, tid, loc_id)
    role_id = await make_role(db, tid)
    user_id = await make_user(db, tid, role_id)
    product_id = await make_product(db, tid)

    session = await pos_svc.open_session(
        db, CashSessionOpen(location_id=loc_id, user_id=user_id)
    )

    original = await pos_svc.create_sale(
        db,
        SaleCreate(
            transaction_uuid=uuid.uuid4(),
            cash_session_id=session.id,
            location_id=loc_id,
            user_id=user_id,
            lines=[make_sale_line(product_id)],
            payments=[PaymentCreate(method="cash", amount=Decimal("20.00"))],
        ),
    )

    return_sale = await pos_svc.void_sale(db, original.id, user_id)
    assert return_sale is not None
    assert return_sale.sale_type == "return"
    assert return_sale.original_sale_id == original.id
    assert return_sale.total == original.total


@pytest.mark.asyncio
async def test_list_sales_by_session(db: AsyncSession):
    tid = await make_tenant(db)
    loc_id = await make_location(db, tid)
    await make_warehouse(db, tid, loc_id)
    role_id = await make_role(db, tid)
    user_id = await make_user(db, tid, role_id)
    product_id = await make_product(db, tid)

    session1 = await pos_svc.open_session(
        db, CashSessionOpen(location_id=loc_id, user_id=user_id)
    )
    session2 = await pos_svc.open_session(
        db, CashSessionOpen(location_id=loc_id, user_id=user_id)
    )

    for _ in range(3):
        await pos_svc.create_sale(
            db,
            SaleCreate(
                transaction_uuid=uuid.uuid4(),
                cash_session_id=session1.id,
                location_id=loc_id,
                user_id=user_id,
                lines=[make_sale_line(product_id)],
                payments=[PaymentCreate(method="card", amount=Decimal("20.00"))],
            ),
        )

    await pos_svc.create_sale(
        db,
        SaleCreate(
            transaction_uuid=uuid.uuid4(),
            cash_session_id=session2.id,
            location_id=loc_id,
            user_id=user_id,
            lines=[make_sale_line(product_id)],
            payments=[PaymentCreate(method="card", amount=Decimal("20.00"))],
        ),
    )

    sales_s1 = await pos_svc.list_sales(db, session_id=session1.id)
    assert len(sales_s1) == 3

    sales_s2 = await pos_svc.list_sales(db, session_id=session2.id)
    assert len(sales_s2) == 1
