"""Read-only catalog — served from edge replica (no cloud call needed)."""
import uuid

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.db import get_db
from app.models.catalog import Barcode, Price, Product

router = APIRouter(prefix="/catalog", tags=["catalog"])


def _product_dict(p: Product) -> dict:
    return {
        "id": str(p.id), "plu": p.plu, "name": p.name,
        "vat_rate": str(p.vat_rate), "unit": p.unit,
        "is_weighable": p.is_weighable, "weight_grams": p.weight_grams,
        "weight_tolerance_pct": str(p.weight_tolerance_pct) if p.weight_tolerance_pct else None,
        "age_restricted": p.age_restricted, "min_age": p.min_age,
        "allergens": p.allergens, "is_active": p.is_active,
        "tenant_id": str(p.tenant_id),
    }


def _price_dict(p: Price) -> dict:
    return {
        "id": str(p.id), "product_id": str(p.product_id),
        "price_type": p.price_type, "amount": str(p.amount),
        "is_active": p.is_active, "location_id": None,
    }


@router.get("/products/by-barcode/{code}")
async def get_by_barcode(code: str, db: AsyncSession = Depends(get_db)):
    result = await db.execute(
        select(Product).join(Barcode).where(Barcode.code == code, Product.deleted_at.is_(None))
    )
    p = result.scalar_one_or_none()
    if not p:
        raise HTTPException(404, "Product not found")
    return _product_dict(p)


@router.get("/products/by-plu/{plu}")
async def get_by_plu(plu: str, tenant_id: uuid.UUID = Query(...), db: AsyncSession = Depends(get_db)):
    result = await db.execute(
        select(Product).where(Product.plu == plu, Product.deleted_at.is_(None))
    )
    p = result.scalar_one_or_none()
    if not p:
        raise HTTPException(404, "Product not found")
    return _product_dict(p)


@router.get("/products/{product_id}")
async def get_product(product_id: uuid.UUID, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(Product).where(Product.id == product_id))
    p = result.scalar_one_or_none()
    if not p:
        raise HTTPException(404, "Product not found")
    return _product_dict(p)


@router.get("/products/{product_id}/prices")
async def get_prices(product_id: uuid.UUID, db: AsyncSession = Depends(get_db)):
    result = await db.execute(
        select(Price).where(Price.product_id == product_id, Price.is_active.is_(True))
    )
    return [_price_dict(p) for p in result.scalars().all()]
