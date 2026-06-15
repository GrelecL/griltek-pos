"""Tests for FURS fiscal service (Step 5)."""
import uuid
from datetime import datetime, timezone
from decimal import Decimal
from unittest.mock import patch

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

import app.services.auth as auth_svc
import app.services.fiscal as fiscal_svc
import app.services.pos as pos_svc
import app.services.tenant as tenant_svc
from app.adapters.furs.zoi import compute_zoi_mock
from app.models.location import Location, LocationConfig
from app.schemas.pos import CashSessionOpen, PaymentCreate, SaleCreate, SaleLineCreate
from app.schemas.tenant import TenantCreate

# ── Seed helpers ──────────────────────────────────────────────────────────────

async def _make_tenant(db: AsyncSession) -> uuid.UUID:
    t = await tenant_svc.create_tenant(
        db, TenantCreate(name="Fiscal Tenant", slug=f"fiscal-{uuid.uuid4().hex[:6]}")
    )
    return t.id


async def _make_location(
    db: AsyncSession,
    tenant_id: uuid.UUID,
    furs_enabled: bool = True,
    tax_number: str | None = "12345678",
    business_premise_id: str | None = "PP001",
) -> uuid.UUID:
    loc = Location(
        tenant_id=tenant_id,
        name="Fiscal Store",
        furs_tax_number=tax_number,
        furs_business_premise_id=business_premise_id,
    )
    db.add(loc)
    await db.flush()

    config = LocationConfig(location_id=loc.id, furs_enabled=furs_enabled)
    db.add(config)
    await db.commit()
    await db.refresh(loc)
    return loc.id


async def _make_user_and_session(db: AsyncSession, tenant_id: uuid.UUID, location_id: uuid.UUID):
    """Seed a role, user, and open cash session. Returns (user_id, session_id)."""
    from app.schemas.auth import RoleCreate, UserCreate
    role = await auth_svc.create_role(
        db,
        RoleCreate(tenant_id=tenant_id, name="cashier", permissions=["sale.create"]),
    )
    user = await auth_svc.create_user(
        db,
        UserCreate(
            tenant_id=tenant_id,
            role_id=role.id,
            username=f"u{uuid.uuid4().hex[:4]}",
            display_name="Cashier",
            pin="1234",
        ),
    )
    session = await pos_svc.open_session(
        db,
        CashSessionOpen(location_id=location_id, user_id=user.id, opening_float=Decimal("0")),
    )
    return user.id, session.id


async def _make_sale(db: AsyncSession, location_id: uuid.UUID, user_id: uuid.UUID, session_id: uuid.UUID) -> uuid.UUID:
    sale = await pos_svc.create_sale(
        db,
        SaleCreate(
            transaction_uuid=uuid.uuid4(),
            location_id=location_id,
            user_id=user_id,
            cash_session_id=session_id,
            lines=[
                SaleLineCreate(
                    product_id=uuid.uuid4(),
                    product_name="Widget",
                    plu="W001",
                    qty=Decimal("1"),
                    unit_price=Decimal("10.00"),
                    vat_rate=Decimal("22"),
                )
            ],
            payments=[
                PaymentCreate(method="cash", amount=Decimal("10.00")),
            ],
        ),
    )
    return sale.id


# ── Tests ──────────────────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_fiscalize_with_furs_enabled(db: AsyncSession):
    tid = await _make_tenant(db)
    loc_id = await _make_location(db, tid, furs_enabled=True, tax_number="12345678", business_premise_id="PP001")
    user_id, session_id = await _make_user_and_session(db, tid, loc_id)
    sale_id = await _make_sale(db, loc_id, user_id, session_id)

    record = await fiscal_svc.fiscalize_sale(db, sale_id, loc_id, Decimal("10.00"))

    assert record.status == "confirmed"
    assert record.zoi is not None
    assert len(record.zoi) == 32
    assert record.eor is not None
    assert record.invoice_number.startswith("PP001")


@pytest.mark.asyncio
async def test_fiscalize_skipped_when_disabled(db: AsyncSession):
    tid = await _make_tenant(db)
    loc_id = await _make_location(db, tid, furs_enabled=False)
    user_id, session_id = await _make_user_and_session(db, tid, loc_id)
    sale_id = await _make_sale(db, loc_id, user_id, session_id)

    record = await fiscal_svc.fiscalize_sale(db, sale_id, loc_id, Decimal("10.00"))

    assert record.status == "skipped"
    assert record.zoi is None
    assert record.eor is None
    assert record.invoice_number == "N/A"


@pytest.mark.asyncio
async def test_fiscal_counter_increments(db: AsyncSession):
    tid = await _make_tenant(db)
    loc_id = await _make_location(db, tid, furs_enabled=True, tax_number="12345678", business_premise_id="PP001")
    user_id, session_id = await _make_user_and_session(db, tid, loc_id)

    sale_id_1 = await _make_sale(db, loc_id, user_id, session_id)
    sale_id_2 = await _make_sale(db, loc_id, user_id, session_id)

    record1 = await fiscal_svc.fiscalize_sale(db, sale_id_1, loc_id, Decimal("10.00"))
    record2 = await fiscal_svc.fiscalize_sale(db, sale_id_2, loc_id, Decimal("20.00"))

    # Both invoice numbers should be for PP001-B1; second should end with -2
    assert record1.invoice_number.endswith("-1")
    assert record2.invoice_number.endswith("-2")


@pytest.mark.asyncio
async def test_get_pending_records(db: AsyncSession):
    tid = await _make_tenant(db)
    loc_id = await _make_location(db, tid, furs_enabled=True, tax_number="12345678", business_premise_id="PP001")
    user_id, session_id = await _make_user_and_session(db, tid, loc_id)
    sale_id = await _make_sale(db, loc_id, user_id, session_id)

    with patch("app.adapters.furs.adapter.MockFursAdapter.confirm_invoice", side_effect=RuntimeError("FURS offline")):
        record = await fiscal_svc.fiscalize_sale(db, sale_id, loc_id, Decimal("10.00"))

    assert record.status == "pending"
    assert record.eor is None
    assert record.zoi is not None  # ZOI computed locally even on failure

    pending = await fiscal_svc.get_pending_records(db, loc_id)
    assert len(pending) == 1
    assert pending[0].id == record.id


@pytest.mark.asyncio
async def test_retry_pending(db: AsyncSession):
    tid = await _make_tenant(db)
    loc_id = await _make_location(db, tid, furs_enabled=True, tax_number="12345678", business_premise_id="PP001")
    user_id, session_id = await _make_user_and_session(db, tid, loc_id)
    sale_id = await _make_sale(db, loc_id, user_id, session_id)

    with patch("app.adapters.furs.adapter.MockFursAdapter.confirm_invoice", side_effect=RuntimeError("FURS offline")):
        record = await fiscal_svc.fiscalize_sale(db, sale_id, loc_id, Decimal("10.00"))

    assert record.status == "pending"

    # Now retry — adapter works normally again
    retried = await fiscal_svc.retry_pending(db, record)
    assert retried.status == "confirmed"
    assert retried.eor is not None


@pytest.mark.asyncio
async def test_zoi_mock_is_deterministic(db: AsyncSession):
    issued = datetime(2026, 1, 15, 10, 30, 0, tzinfo=timezone.utc)
    kwargs = dict(
        tax_number="12345678",
        issued_at=issued,
        invoice_number="PP001-B1-1",
        business_premise_id="PP001",
        electronic_device_id="B1",
        invoice_amount=Decimal("10.00"),
    )
    zoi1 = compute_zoi_mock(**kwargs)
    zoi2 = compute_zoi_mock(**kwargs)

    assert zoi1 == zoi2
    assert len(zoi1) == 32
    assert all(c in "0123456789abcdef" for c in zoi1)


@pytest.mark.asyncio
async def test_get_fiscal_record_by_sale(db: AsyncSession):
    tid = await _make_tenant(db)
    loc_id = await _make_location(db, tid, furs_enabled=True, tax_number="12345678", business_premise_id="PP001")
    user_id, session_id = await _make_user_and_session(db, tid, loc_id)
    sale_id = await _make_sale(db, loc_id, user_id, session_id)

    record = await fiscal_svc.fiscalize_sale(db, sale_id, loc_id, Decimal("10.00"))

    fetched = await fiscal_svc.get_fiscal_record_by_sale(db, sale_id)
    assert fetched is not None
    assert fetched.id == record.id
    assert fetched.sale_id == sale_id


@pytest.mark.asyncio
async def test_list_fiscal_records_by_status(db: AsyncSession):
    tid = await _make_tenant(db)
    loc_id = await _make_location(db, tid, furs_enabled=True, tax_number="12345678", business_premise_id="PP001")
    user_id, session_id = await _make_user_and_session(db, tid, loc_id)

    # Create a confirmed record (furs_enabled=True)
    sale_id_confirmed = await _make_sale(db, loc_id, user_id, session_id)
    await fiscal_svc.fiscalize_sale(db, sale_id_confirmed, loc_id, Decimal("10.00"))

    # Create a skipped record by temporarily using a location with furs_enabled=False
    loc_id_disabled = await _make_location(db, tid, furs_enabled=False)
    user_id2, session_id2 = await _make_user_and_session(db, tid, loc_id_disabled)
    sale_id_skipped = await _make_sale(db, loc_id_disabled, user_id2, session_id2)
    await fiscal_svc.fiscalize_sale(db, sale_id_skipped, loc_id_disabled, Decimal("5.00"))

    confirmed_records = await fiscal_svc.list_fiscal_records(db, loc_id, status="confirmed")
    assert len(confirmed_records) == 1
    assert confirmed_records[0].status == "confirmed"

    skipped_records = await fiscal_svc.list_fiscal_records(db, loc_id_disabled, status="skipped")
    assert len(skipped_records) == 1
    assert skipped_records[0].status == "skipped"
