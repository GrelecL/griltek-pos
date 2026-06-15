"""Tests for reports service and audit/GDPR services."""
import uuid
from datetime import datetime, timezone
from decimal import Decimal

import pytest
from sqlalchemy import select

from app.models.audit import AuditLog
from app.models.auth import Role, User
from app.models.catalog import Product
from app.models.customer import Customer
from app.models.fiscal import FiscalRecord
from app.models.location import Location, LocationConfig
from app.models.pos import CashSession, Payment, Sale, SaleLine
from app.models.tenant import Tenant
from app.models.warehouse import StockItem, Warehouse
from app.services.audit import log_action
from app.services.gdpr import erase_customer
from app.services.reports import (
    dashboard_summary,
    fiscal_report,
    payment_method_breakdown,
    rows_to_csv,
    sales_by_product,
    sales_report,
    stock_levels,
    vat_breakdown,
)

# ── fixtures ──────────────────────────────────────────────────────────────────

async def _setup(db):
    """Returns (tenant, location, user, session)."""
    tenant = Tenant(id=uuid.uuid4(), name="T", slug="t")
    db.add(tenant)
    await db.flush()
    loc = Location(id=uuid.uuid4(), tenant_id=tenant.id, name="L", address="A",
                   business_type="retail", timezone="UTC")
    db.add(loc)
    await db.flush()
    cfg = LocationConfig(id=uuid.uuid4(), location_id=loc.id)
    db.add(cfg)
    role = Role(id=uuid.uuid4(), tenant_id=tenant.id, name="r", permissions=[])
    db.add(role)
    await db.flush()
    user = User(id=uuid.uuid4(), tenant_id=tenant.id, role_id=role.id,
                username="u", display_name="U", pin_hash="x")
    db.add(user)
    await db.flush()
    session = CashSession(id=uuid.uuid4(), location_id=loc.id, user_id=user.id,
                          status="open", opening_float=Decimal("0"))
    db.add(session)
    await db.flush()
    return tenant, loc, user, session


async def _make_sale(db, loc_id, session_id, user_id, total=Decimal("10.00"), sale_type="sale") -> Sale:
    sale = Sale(
        id=uuid.uuid4(), transaction_uuid=uuid.uuid4(),
        cash_session_id=session_id, location_id=loc_id, user_id=user_id,
        sale_type=sale_type, status="completed",
        subtotal=total, discount_total=Decimal("0"),
        vat_total=(total * Decimal("0.095") / Decimal("1.095")).quantize(Decimal("0.01")),
        total=total,
    )
    db.add(sale)
    await db.flush()
    vat_amount = (total * Decimal("0.095") / Decimal("1.095")).quantize(Decimal("0.01"))
    db.add(SaleLine(
        id=uuid.uuid4(), sale_id=sale.id, product_id=uuid.uuid4(),
        product_name="Mleko", plu="001", qty=Decimal("1"),
        unit_price=total, vat_rate=Decimal("9.5"),
        line_total=total, vat_amount=vat_amount,
        discount_pct=Decimal("0"), discount_amount=Decimal("0"),
    ))
    db.add(Payment(id=uuid.uuid4(), sale_id=sale.id, method="cash", amount=total, status="completed"))
    return sale


_START = datetime(2026, 1, 1, tzinfo=timezone.utc)
_END   = datetime(2026, 12, 31, 23, 59, 59, tzinfo=timezone.utc)


# ── audit log ─────────────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_log_action(db):
    entry = await log_action(db, "test_event", resource_type="sale", resource_id="s1")
    await db.commit()
    result = await db.execute(select(AuditLog).where(AuditLog.id == entry.id))
    found = result.scalar_one()
    assert found.action == "test_event"
    assert found.resource_id == "s1"


@pytest.mark.asyncio
async def test_log_action_with_detail(db):
    entry = await log_action(db, "config_change", detail={"key": "furs_enabled", "value": True})
    await db.commit()
    await db.refresh(entry)
    assert entry.detail["key"] == "furs_enabled"


# ── GDPR ─────────────────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_gdpr_erase_customer(db):
    tenant = Tenant(id=uuid.uuid4(), name="T2", slug="t2")
    db.add(tenant)
    await db.flush()
    customer = Customer(id=uuid.uuid4(), tenant_id=tenant.id,
                        name="Jana Kovač", email="jana@test.si", phone="041000000")
    db.add(customer)
    await db.commit()

    await erase_customer(db, customer.id)
    await db.commit()

    await db.refresh(customer)
    assert customer.name == "ERASED"
    assert customer.email is None
    assert customer.phone is None


@pytest.mark.asyncio
async def test_gdpr_erase_writes_audit_log(db):
    tenant = Tenant(id=uuid.uuid4(), name="T3", slug="t3")
    db.add(tenant)
    await db.flush()
    customer = Customer(id=uuid.uuid4(), tenant_id=tenant.id, name="Bob")
    db.add(customer)
    await db.flush()

    uid = uuid.uuid4()
    await erase_customer(db, customer.id, requesting_user_id=uid, tenant_id=tenant.id)
    await db.commit()

    result = await db.execute(
        select(AuditLog).where(AuditLog.action == "customer_erasure")
    )
    entry = result.scalar_one()
    assert str(entry.resource_id) == str(customer.id)
    assert entry.user_id == uid


# ── dashboard ─────────────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_dashboard_summary(db):
    tenant, loc, user, session = await _setup(db)
    await _make_sale(db, loc.id, session.id, user.id, Decimal("25.00"))
    await _make_sale(db, loc.id, session.id, user.id, Decimal("15.00"))
    await db.commit()

    result = await dashboard_summary(db, loc.id, _START, _END)
    assert result["sales"]["count"] == 2
    assert Decimal(result["sales"]["revenue"]) == Decimal("40.00")


# ── sales report ──────────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_sales_report_rows(db):
    tenant, loc, user, session = await _setup(db)
    await _make_sale(db, loc.id, session.id, user.id, Decimal("10.00"))
    await _make_sale(db, loc.id, session.id, user.id, Decimal("20.00"))
    await db.commit()

    rows = await sales_report(db, loc.id, _START, _END)
    assert len(rows) == 2
    totals = {Decimal(r["total"]) for r in rows}
    assert Decimal("10.00") in totals
    assert Decimal("20.00") in totals


@pytest.mark.asyncio
async def test_sales_by_product(db):
    tenant, loc, user, session = await _setup(db)
    await _make_sale(db, loc.id, session.id, user.id, Decimal("5.00"))
    await _make_sale(db, loc.id, session.id, user.id, Decimal("5.00"))
    await db.commit()

    rows = await sales_by_product(db, loc.id, _START, _END)
    assert len(rows) >= 1
    assert rows[0]["plu"] == "001"
    assert Decimal(rows[0]["total_revenue"]) == Decimal("10.00")


@pytest.mark.asyncio
async def test_payment_method_breakdown(db):
    tenant, loc, user, session = await _setup(db)
    await _make_sale(db, loc.id, session.id, user.id, Decimal("12.00"))
    await db.commit()

    rows = await payment_method_breakdown(db, loc.id, _START, _END)
    assert any(r["method"] == "cash" for r in rows)


@pytest.mark.asyncio
async def test_vat_breakdown(db):
    tenant, loc, user, session = await _setup(db)
    await _make_sale(db, loc.id, session.id, user.id, Decimal("10.00"))
    await db.commit()

    rows = await vat_breakdown(db, loc.id, _START, _END)
    assert len(rows) >= 1
    assert any(Decimal(r["vat_rate"]) == Decimal("9.5") for r in rows)


# ── stock ─────────────────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_stock_levels(db):
    tenant = Tenant(id=uuid.uuid4(), name="T4", slug="t4")
    db.add(tenant)
    loc = Location(id=uuid.uuid4(), tenant_id=tenant.id, name="L", address="A",
                   business_type="retail", timezone="UTC")
    db.add(loc)
    await db.flush()
    cfg = LocationConfig(id=uuid.uuid4(), location_id=loc.id)
    db.add(cfg)
    wh = Warehouse(id=uuid.uuid4(), tenant_id=tenant.id, location_id=loc.id,
                   name="Main", is_default=True)
    db.add(wh)
    product = Product(id=uuid.uuid4(), tenant_id=tenant.id,
                      plu="999", name="Test", vat_rate=Decimal("9.5"),
                      unit="piece", is_weighable=False, age_restricted=False,
                      allergens=[], is_active=True)
    db.add(product)
    await db.flush()
    db.add(StockItem(id=uuid.uuid4(), product_id=product.id, warehouse_id=wh.id,
                     qty=Decimal("50"), reserved_qty=Decimal("0"), min_stock=Decimal("5")))
    await db.commit()

    rows = await stock_levels(db, wh.id)
    assert len(rows) == 1
    assert rows[0]["plu"] == "999"
    assert rows[0]["is_low"] is False


@pytest.mark.asyncio
async def test_stock_low_stock_filter(db):
    tenant = Tenant(id=uuid.uuid4(), name="T5", slug="t5")
    db.add(tenant)
    loc = Location(id=uuid.uuid4(), tenant_id=tenant.id, name="L", address="A",
                   business_type="retail", timezone="UTC")
    db.add(loc)
    await db.flush()
    cfg = LocationConfig(id=uuid.uuid4(), location_id=loc.id)
    db.add(cfg)
    wh = Warehouse(id=uuid.uuid4(), tenant_id=tenant.id, location_id=loc.id,
                   name="Main", is_default=True)
    db.add(wh)
    product = Product(id=uuid.uuid4(), tenant_id=tenant.id,
                      plu="888", name="Low", vat_rate=Decimal("9.5"),
                      unit="piece", is_weighable=False, age_restricted=False,
                      allergens=[], is_active=True)
    db.add(product)
    await db.flush()
    db.add(StockItem(id=uuid.uuid4(), product_id=product.id, warehouse_id=wh.id,
                     qty=Decimal("2"), reserved_qty=Decimal("0"), min_stock=Decimal("10")))
    await db.commit()

    rows = await stock_levels(db, wh.id, low_stock_only=True)
    assert len(rows) == 1
    assert rows[0]["is_low"] is True


# ── CSV export ────────────────────────────────────────────────────────────────

def test_rows_to_csv_basic():
    rows = [{"a": 1, "b": 2}, {"a": 3, "b": 4}]
    csv = rows_to_csv(rows)
    assert "a,b" in csv
    assert "1,2" in csv
    assert "3,4" in csv


def test_rows_to_csv_empty():
    assert rows_to_csv([]) == ""


# ── fiscal report ─────────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_fiscal_report_counts(db):
    tenant = Tenant(id=uuid.uuid4(), name="T6", slug="t6")
    db.add(tenant)
    loc = Location(id=uuid.uuid4(), tenant_id=tenant.id, name="L", address="A",
                   business_type="retail", timezone="UTC")
    db.add(loc)
    await db.flush()
    cfg = LocationConfig(id=uuid.uuid4(), location_id=loc.id)
    db.add(cfg)
    role = Role(id=uuid.uuid4(), tenant_id=tenant.id, name="r", permissions=[])
    db.add(role)
    await db.flush()
    user = User(id=uuid.uuid4(), tenant_id=tenant.id, role_id=role.id,
                username="u2", display_name="U", pin_hash="x")
    db.add(user)
    await db.flush()
    session = CashSession(id=uuid.uuid4(), location_id=loc.id, user_id=user.id,
                          status="open", opening_float=Decimal("0"))
    db.add(session)
    await db.flush()

    for status in ["confirmed", "confirmed", "pending"]:
        sale = Sale(
            id=uuid.uuid4(), transaction_uuid=uuid.uuid4(),
            cash_session_id=session.id, location_id=loc.id, user_id=user.id,
            sale_type="sale", status="completed",
            subtotal=Decimal("1"), discount_total=Decimal("0"),
            vat_total=Decimal("0"), total=Decimal("1"),
        )
        db.add(sale)
        await db.flush()
        db.add(FiscalRecord(
            id=uuid.uuid4(), sale_id=sale.id, location_id=loc.id,
            invoice_number=f"PP-1-{uuid.uuid4().hex[:4]}",
            business_premise_id="PP", electronic_device_id="B1",
            invoice_amount=Decimal("1.00"),
            zoi=uuid.uuid4().hex[:32], eor=str(uuid.uuid4()),
            status=status,
        ))
    await db.commit()

    result = await fiscal_report(db, _START, _END)
    assert result["confirmed"] == 2
    assert result["pending"] == 1
    assert result["total"] == 3
