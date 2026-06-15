"""
SQLite local cache — Level 3 fallback when store-server is unreachable.
Populated from last successful sync. Sales queued here until connectivity restored.
"""
import datetime
import json
import sqlite3
from pathlib import Path

DB_PATH = Path.home() / ".griltek" / "local_cache.db"


def _conn() -> sqlite3.Connection:
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(str(DB_PATH))
    conn.row_factory = sqlite3.Row
    return conn


def init_db() -> None:
    with _conn() as conn:
        conn.executescript("""
            CREATE TABLE IF NOT EXISTS products (
                id TEXT PRIMARY KEY,
                plu TEXT NOT NULL,
                name TEXT NOT NULL,
                vat_rate TEXT NOT NULL,
                unit TEXT NOT NULL DEFAULT 'piece',
                is_weighable INTEGER NOT NULL DEFAULT 0,
                weight_grams INTEGER,
                weight_tolerance_pct TEXT,
                age_restricted INTEGER NOT NULL DEFAULT 0,
                min_age INTEGER,
                allergens TEXT DEFAULT '[]',
                is_active INTEGER NOT NULL DEFAULT 1
            );
            CREATE TABLE IF NOT EXISTS prices (
                id TEXT PRIMARY KEY,
                product_id TEXT NOT NULL,
                price_type TEXT NOT NULL DEFAULT 'regular',
                amount TEXT NOT NULL,
                is_active INTEGER NOT NULL DEFAULT 1
            );
            CREATE TABLE IF NOT EXISTS barcodes (
                code TEXT PRIMARY KEY,
                product_id TEXT NOT NULL
            );
            CREATE TABLE IF NOT EXISTS offline_sales (
                id TEXT PRIMARY KEY,
                payload TEXT NOT NULL,
                created_at TEXT NOT NULL,
                synced INTEGER NOT NULL DEFAULT 0
            );
        """)


def upsert_product(p: dict) -> None:
    with _conn() as conn:
        conn.execute(
            """INSERT OR REPLACE INTO products
               (id,plu,name,vat_rate,unit,is_weighable,weight_grams,
                weight_tolerance_pct,age_restricted,min_age,allergens,is_active)
               VALUES (?,?,?,?,?,?,?,?,?,?,?,?)""",
            (
                p["id"], p["plu"], p["name"], str(p["vat_rate"]),
                p.get("unit", "piece"), int(p.get("is_weighable", False)),
                p.get("weight_grams"),
                str(p["weight_tolerance_pct"]) if p.get("weight_tolerance_pct") else None,
                int(p.get("age_restricted", False)), p.get("min_age"),
                json.dumps(p.get("allergens", [])), int(p.get("is_active", True)),
            ),
        )


def upsert_price(price: dict) -> None:
    with _conn() as conn:
        conn.execute(
            "INSERT OR REPLACE INTO prices (id,product_id,price_type,amount,is_active) VALUES (?,?,?,?,?)",
            (
                price["id"], price["product_id"],
                price.get("price_type", "regular"), str(price["amount"]),
                int(price.get("is_active", True)),
            ),
        )


def upsert_barcode(code: str, product_id: str) -> None:
    with _conn() as conn:
        conn.execute(
            "INSERT OR REPLACE INTO barcodes (code,product_id) VALUES (?,?)", (code, product_id)
        )


def get_product_by_barcode(code: str) -> dict | None:
    with _conn() as conn:
        row = conn.execute(
            "SELECT p.* FROM products p JOIN barcodes b ON p.id=b.product_id WHERE b.code=?",
            (code,),
        ).fetchone()
        return dict(row) if row else None


def get_product_by_plu(plu: str) -> dict | None:
    with _conn() as conn:
        row = conn.execute(
            "SELECT * FROM products WHERE plu=? AND is_active=1", (plu,)
        ).fetchone()
        return dict(row) if row else None


def get_prices(product_id: str) -> list[dict]:
    with _conn() as conn:
        rows = conn.execute(
            "SELECT * FROM prices WHERE product_id=? AND is_active=1", (product_id,)
        ).fetchall()
        return [dict(r) for r in rows]


def save_offline_sale(sale_id: str, payload: str) -> None:
    with _conn() as conn:
        conn.execute(
            "INSERT INTO offline_sales (id,payload,created_at) VALUES (?,?,?)",
            (sale_id, payload, datetime.datetime.utcnow().isoformat()),
        )


def pending_offline_sales() -> list[dict]:
    with _conn() as conn:
        rows = conn.execute("SELECT * FROM offline_sales WHERE synced=0").fetchall()
        return [dict(r) for r in rows]


def mark_sale_synced(sale_id: str) -> None:
    with _conn() as conn:
        conn.execute("UPDATE offline_sales SET synced=1 WHERE id=?", (sale_id,))
