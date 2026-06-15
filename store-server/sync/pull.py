"""Pull sync: fetch delta catalog from cloud API and upsert into edge replica."""
import uuid
from datetime import datetime, timezone

import httpx
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.models.catalog import Barcode, Price, Product
from app.models.live import SyncCursorRecord


async def _set_cursor(db: AsyncSession, entity_type: str, version: int) -> None:
    result = await db.execute(
        select(SyncCursorRecord).where(SyncCursorRecord.entity_type == entity_type)
    )
    cursor = result.scalar_one_or_none()
    if cursor:
        cursor.pull_version = version
        cursor.last_pulled_at = datetime.now(timezone.utc)
        cursor.version += 1
    else:
        db.add(SyncCursorRecord(
            entity_type=entity_type,
            pull_version=version,
            last_pulled_at=datetime.now(timezone.utc),
        ))
    await db.flush()


async def pull_products(db: AsyncSession) -> dict:
    tenant_id = settings.tenant_id
    if not settings.cloud_api_url or not tenant_id:
        return {"skipped": True, "reason": "cloud_api_url or tenant_id not configured"}
    try:
        async with httpx.AsyncClient(base_url=settings.cloud_api_url, timeout=30.0) as client:
            resp = await client.get("/catalog/products", params={"tenant_id": tenant_id, "limit": 1000})
            if resp.status_code != 200:
                return {"error": f"HTTP {resp.status_code}"}
            products = resp.json()
    except httpx.RequestError as e:
        return {"error": str(e), "wan_down": True}

    upserted = 0
    for p in products:
        cloud_id = uuid.UUID(p["id"])
        result = await db.execute(select(Product).where(Product.cloud_id == cloud_id))
        existing = result.scalar_one_or_none()
        if existing:
            existing.name = p["name"]
            existing.plu = p["plu"]
            existing.vat_rate = p["vat_rate"]
            existing.unit = p["unit"]
            existing.is_weighable = p["is_weighable"]
            existing.weight_grams = p.get("weight_grams")
            existing.allergens = p.get("allergens", [])
            existing.is_active = p["is_active"]
            existing.version += 1
        else:
            db.add(Product(
                id=cloud_id, cloud_id=cloud_id,
                tenant_id=uuid.UUID(p["tenant_id"]),
                plu=p["plu"], name=p["name"],
                vat_rate=p["vat_rate"], unit=p["unit"],
                is_weighable=p["is_weighable"],
                weight_grams=p.get("weight_grams"),
                age_restricted=p["age_restricted"],
                min_age=p.get("min_age"),
                allergens=p.get("allergens", []),
                is_active=p["is_active"],
            ))
        upserted += 1

    await _set_cursor(db, "products", upserted)
    await db.commit()
    return {"upserted": upserted}


async def pull_barcodes(db: AsyncSession) -> dict:
    if not settings.cloud_api_url:
        return {"skipped": True}
    result = await db.execute(select(Product))
    products = list(result.scalars().all())
    upserted = 0
    try:
        async with httpx.AsyncClient(base_url=settings.cloud_api_url, timeout=30.0) as client:
            for product in products:
                resp = await client.get(f"/catalog/products/{product.cloud_id}/barcodes")
                if resp.status_code != 200:
                    continue
                for b in resp.json():
                    cloud_id = uuid.UUID(b["id"])
                    r2 = await db.execute(select(Barcode).where(Barcode.cloud_id == cloud_id))
                    if not r2.scalar_one_or_none():
                        db.add(Barcode(
                            id=cloud_id, cloud_id=cloud_id,
                            product_id=product.id,
                            code=b["code"], barcode_type=b["barcode_type"],
                        ))
                        upserted += 1
    except httpx.RequestError as e:
        return {"error": str(e), "wan_down": True}
    await db.commit()
    return {"upserted": upserted}


async def pull_prices(db: AsyncSession) -> dict:
    if not settings.cloud_api_url:
        return {"skipped": True}
    result = await db.execute(select(Product))
    products = list(result.scalars().all())
    upserted = 0
    try:
        async with httpx.AsyncClient(base_url=settings.cloud_api_url, timeout=30.0) as client:
            for product in products:
                resp = await client.get(f"/catalog/products/{product.cloud_id}/prices")
                if resp.status_code != 200:
                    continue
                for p in resp.json():
                    cloud_id = uuid.UUID(p["id"])
                    r2 = await db.execute(select(Price).where(Price.cloud_id == cloud_id))
                    existing = r2.scalar_one_or_none()
                    if existing:
                        existing.amount = p["amount"]
                        existing.is_active = p["is_active"]
                        existing.version += 1
                    else:
                        db.add(Price(
                            id=cloud_id, cloud_id=cloud_id,
                            product_id=product.id,
                            price_type=p["price_type"],
                            amount=p["amount"], is_active=p["is_active"],
                        ))
                    upserted += 1
    except httpx.RequestError as e:
        return {"error": str(e), "wan_down": True}
    await db.commit()
    return {"upserted": upserted}


async def run_full_pull(db: AsyncSession) -> dict:
    products_result = await pull_products(db)
    if products_result.get("wan_down"):
        return {"wan_down": True, "products": products_result}
    barcodes_result = await pull_barcodes(db)
    prices_result = await pull_prices(db)
    return {"products": products_result, "barcodes": barcodes_result, "prices": prices_result}
