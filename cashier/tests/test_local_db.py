"""Tests for cashier Level-3 SQLite fallback cache."""
import json

import pytest


@pytest.fixture(autouse=True)
def _patch_db_path(tmp_path, monkeypatch):
    import cashier.local.db as db_mod
    monkeypatch.setattr(db_mod, "DB_PATH", tmp_path / "test_cache.db")


def test_init_db():
    import cashier.local.db as db
    db.init_db()  # should not raise


def test_upsert_and_get_product_by_plu():
    import cashier.local.db as db
    db.init_db()
    db.upsert_product({
        "id": "prod-1", "plu": "100", "name": "Mleko",
        "vat_rate": "9.5", "unit": "piece", "is_weighable": False,
        "age_restricted": False, "allergens": [], "is_active": True,
    })
    found = db.get_product_by_plu("100")
    assert found is not None
    assert found["name"] == "Mleko"


def test_get_product_by_barcode():
    import cashier.local.db as db
    db.init_db()
    db.upsert_product({
        "id": "prod-2", "plu": "200", "name": "Jogurt",
        "vat_rate": "9.5", "unit": "piece", "is_weighable": False,
        "age_restricted": False, "allergens": [], "is_active": True,
    })
    db.upsert_barcode("3838003819303", "prod-2")
    found = db.get_product_by_barcode("3838003819303")
    assert found is not None
    assert found["name"] == "Jogurt"


def test_get_prices():
    import cashier.local.db as db
    db.init_db()
    db.upsert_product({
        "id": "prod-3", "plu": "300", "name": "Sir",
        "vat_rate": "9.5", "unit": "kg", "is_weighable": True,
        "age_restricted": False, "allergens": [], "is_active": True,
    })
    db.upsert_price({"id": "price-1", "product_id": "prod-3", "price_type": "regular", "amount": "3.99"})
    prices = db.get_prices("prod-3")
    assert len(prices) == 1
    assert prices[0]["amount"] == "3.99"


def test_save_and_list_offline_sales():
    import cashier.local.db as db
    db.init_db()
    db.save_offline_sale("sale-001", json.dumps({"lines": []}))
    db.save_offline_sale("sale-002", json.dumps({"lines": []}))
    pending = db.pending_offline_sales()
    assert len(pending) == 2


def test_mark_sale_synced():
    import cashier.local.db as db
    db.init_db()
    db.save_offline_sale("sale-003", json.dumps({}))
    db.mark_sale_synced("sale-003")
    pending = db.pending_offline_sales()
    ids = [s["id"] for s in pending]
    assert "sale-003" not in ids


def test_upsert_product_update():
    import cashier.local.db as db
    db.init_db()
    db.upsert_product({
        "id": "prod-4", "plu": "400", "name": "Kruh",
        "vat_rate": "9.5", "unit": "piece", "is_weighable": False,
        "age_restricted": False, "allergens": [], "is_active": True,
    })
    db.upsert_product({
        "id": "prod-4", "plu": "400", "name": "Kruh Integral",
        "vat_rate": "9.5", "unit": "piece", "is_weighable": False,
        "age_restricted": False, "allergens": [], "is_active": True,
    })
    found = db.get_product_by_plu("400")
    assert found["name"] == "Kruh Integral"
