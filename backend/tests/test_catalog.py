import uuid
from decimal import Decimal

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

import app.services.catalog as svc
import app.services.tenant as tenant_svc
from app.schemas.catalog import (
    BarcodeCreate,
    CategoryCreate,
    CategoryUpdate,
    PriceCreate,
    PriceUpdate,
    ProductCreate,
    ProductUpdate,
)
from app.schemas.tenant import TenantCreate


@pytest.fixture
def tenant_id():
    return uuid.uuid4()


async def make_tenant(db: AsyncSession) -> uuid.UUID:
    t = await tenant_svc.create_tenant(db, TenantCreate(name="Test Tenant", slug=f"test-{uuid.uuid4().hex[:6]}"))
    return t.id


@pytest.mark.asyncio
async def test_create_and_get_category(db: AsyncSession):
    tid = await make_tenant(db)
    cat = await svc.create_category(db, CategoryCreate(tenant_id=tid, name="Drinks", slug="drinks"))
    assert cat.id is not None
    assert cat.name == "Drinks"

    fetched = await svc.get_category(db, cat.id)
    assert fetched is not None
    assert fetched.slug == "drinks"


@pytest.mark.asyncio
async def test_list_categories(db: AsyncSession):
    tid = await make_tenant(db)
    await svc.create_category(db, CategoryCreate(tenant_id=tid, name="A", slug="a"))
    await svc.create_category(db, CategoryCreate(tenant_id=tid, name="B", slug="b"))
    cats = await svc.list_categories(db, tid)
    assert len(cats) == 2


@pytest.mark.asyncio
async def test_update_category(db: AsyncSession):
    tid = await make_tenant(db)
    cat = await svc.create_category(db, CategoryCreate(tenant_id=tid, name="Old", slug="old"))
    updated = await svc.update_category(db, cat.id, CategoryUpdate(name="New"))
    assert updated.name == "New"
    assert updated.version == 2


@pytest.mark.asyncio
async def test_delete_category(db: AsyncSession):
    tid = await make_tenant(db)
    cat = await svc.create_category(db, CategoryCreate(tenant_id=tid, name="Del", slug="del"))
    result = await svc.delete_category(db, cat.id)
    assert result is True
    fetched = await svc.get_category(db, cat.id)
    assert fetched is None


@pytest.mark.asyncio
async def test_delete_nonexistent_category(db: AsyncSession):
    result = await svc.delete_category(db, uuid.uuid4())
    assert result is False


@pytest.mark.asyncio
async def test_create_and_get_product(db: AsyncSession):
    tid = await make_tenant(db)
    prod = await svc.create_product(db, ProductCreate(
        tenant_id=tid, plu="001", name="Apple", vat_rate=Decimal("9.5"),
    ))
    assert prod.id is not None
    fetched = await svc.get_product(db, prod.id)
    assert fetched.plu == "001"


@pytest.mark.asyncio
async def test_list_products(db: AsyncSession):
    tid = await make_tenant(db)
    await svc.create_product(db, ProductCreate(tenant_id=tid, plu="P1", name="P1"))
    await svc.create_product(db, ProductCreate(tenant_id=tid, plu="P2", name="P2"))
    prods = await svc.list_products(db, tid)
    assert len(prods) == 2


@pytest.mark.asyncio
async def test_update_product(db: AsyncSession):
    tid = await make_tenant(db)
    prod = await svc.create_product(db, ProductCreate(tenant_id=tid, plu="UPD", name="Original"))
    updated = await svc.update_product(db, prod.id, ProductUpdate(name="Updated", is_active=False))
    assert updated.name == "Updated"
    assert updated.is_active is False
    assert updated.version == 2


@pytest.mark.asyncio
async def test_delete_product(db: AsyncSession):
    tid = await make_tenant(db)
    prod = await svc.create_product(db, ProductCreate(tenant_id=tid, plu="DEL", name="ToDelete"))
    assert await svc.delete_product(db, prod.id) is True
    assert await svc.get_product(db, prod.id) is None


@pytest.mark.asyncio
async def test_barcode_lookup(db: AsyncSession):
    tid = await make_tenant(db)
    prod = await svc.create_product(db, ProductCreate(tenant_id=tid, plu="BC1", name="BarcodeProd"))
    await svc.create_barcode(db, BarcodeCreate(product_id=prod.id, code="1234567890123"))
    found = await svc.get_product_by_barcode(db, "1234567890123")
    assert found is not None
    assert found.id == prod.id


@pytest.mark.asyncio
async def test_barcode_lookup_missing(db: AsyncSession):
    result = await svc.get_product_by_barcode(db, "nonexistent")
    assert result is None


@pytest.mark.asyncio
async def test_plu_lookup(db: AsyncSession):
    tid = await make_tenant(db)
    prod = await svc.create_product(db, ProductCreate(tenant_id=tid, plu="PLU42", name="PLUProd"))
    found = await svc.get_product_by_plu(db, tid, "PLU42")
    assert found is not None
    assert found.id == prod.id


@pytest.mark.asyncio
async def test_list_barcodes(db: AsyncSession):
    tid = await make_tenant(db)
    prod = await svc.create_product(db, ProductCreate(tenant_id=tid, plu="BC2", name="Prod"))
    await svc.create_barcode(db, BarcodeCreate(product_id=prod.id, code="111"))
    await svc.create_barcode(db, BarcodeCreate(product_id=prod.id, code="222"))
    barcodes = await svc.list_barcodes(db, prod.id)
    assert len(barcodes) == 2


@pytest.mark.asyncio
async def test_price_create_and_list(db: AsyncSession):
    tid = await make_tenant(db)
    prod = await svc.create_product(db, ProductCreate(tenant_id=tid, plu="PR1", name="PricedProd"))
    price = await svc.create_price(db, PriceCreate(product_id=prod.id, amount=Decimal("9.99")))
    assert price.amount == Decimal("9.99")
    prices = await svc.list_prices(db, prod.id)
    assert len(prices) == 1


@pytest.mark.asyncio
async def test_price_update(db: AsyncSession):
    tid = await make_tenant(db)
    prod = await svc.create_product(db, ProductCreate(tenant_id=tid, plu="PR2", name="PricedProd2"))
    price = await svc.create_price(db, PriceCreate(product_id=prod.id, amount=Decimal("5.00")))
    updated = await svc.update_price(db, price.id, PriceUpdate(amount=Decimal("6.50")))
    assert updated.amount == Decimal("6.50")
    assert updated.version == 2


@pytest.mark.asyncio
async def test_csv_import_valid(db: AsyncSession):
    tid = await make_tenant(db)
    csv_content = "plu,name,vat_rate,unit\nCSV1,CSV Product,22,piece\nCSV2,Another,9.5,kg\n"
    result = await svc.import_products_csv(db, tid, csv_content)
    assert result["created"] == 2
    assert result["updated"] == 0
    assert result["errors"] == []


@pytest.mark.asyncio
async def test_csv_import_update(db: AsyncSession):
    tid = await make_tenant(db)
    # create first
    await svc.create_product(db, ProductCreate(tenant_id=tid, plu="UPD1", name="Original"))
    csv_content = "plu,name,vat_rate\nUPD1,Updated Name,22\n"
    result = await svc.import_products_csv(db, tid, csv_content)
    assert result["created"] == 0
    assert result["updated"] == 1
    prod = await svc.get_product_by_plu(db, tid, "UPD1")
    assert prod.name == "Updated Name"


@pytest.mark.asyncio
async def test_csv_import_error_row(db: AsyncSession):
    tid = await make_tenant(db)
    # missing required 'name' column causes KeyError
    csv_content = "plu,vat_rate\nBAD1,notanumber_that_causes_decimal_error\n"
    result = await svc.import_products_csv(db, tid, csv_content)
    # 'name' key missing -> error
    assert len(result["errors"]) >= 1


@pytest.mark.asyncio
async def test_csv_import_allergens(db: AsyncSession):
    tid = await make_tenant(db)
    csv_content = "plu,name,allergens\nAL1,AllergenProd,gluten;milk;eggs\n"
    result = await svc.import_products_csv(db, tid, csv_content)
    assert result["created"] == 1
    prod = await svc.get_product_by_plu(db, tid, "AL1")
    assert prod.allergens == ["gluten", "milk", "eggs"]
