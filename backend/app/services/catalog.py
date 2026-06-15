import csv
import io
import uuid
from datetime import timezone as _tz
from decimal import Decimal

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.catalog import Barcode, Category, Price, Product
from app.schemas.catalog import (
    BarcodeCreate,
    CategoryCreate,
    CategoryUpdate,
    PriceCreate,
    PriceUpdate,
    ProductCreate,
    ProductUpdate,
)


async def create_category(db: AsyncSession, data: CategoryCreate) -> Category:
    obj = Category(**data.model_dump())
    db.add(obj)
    await db.commit()
    await db.refresh(obj)
    return obj


async def get_category(db: AsyncSession, category_id: uuid.UUID) -> Category | None:
    result = await db.execute(select(Category).where(Category.id == category_id, Category.deleted_at.is_(None)))
    return result.scalar_one_or_none()


async def list_categories(db: AsyncSession, tenant_id: uuid.UUID) -> list[Category]:
    result = await db.execute(
        select(Category)
        .where(Category.tenant_id == tenant_id, Category.deleted_at.is_(None))
        .order_by(Category.sort_order, Category.name)
    )
    return list(result.scalars().all())


async def update_category(db: AsyncSession, category_id: uuid.UUID, data: CategoryUpdate) -> Category | None:
    obj = await get_category(db, category_id)
    if not obj:
        return None
    for k, v in data.model_dump(exclude_none=True).items():
        setattr(obj, k, v)
    obj.version += 1
    await db.commit()
    await db.refresh(obj)
    return obj


async def delete_category(db: AsyncSession, category_id: uuid.UUID) -> bool:
    from datetime import datetime

    obj = await get_category(db, category_id)
    if not obj:
        return False
    obj.deleted_at = datetime.now(_tz.utc)
    await db.commit()
    return True


async def create_product(db: AsyncSession, data: ProductCreate) -> Product:
    obj = Product(**data.model_dump())
    db.add(obj)
    await db.commit()
    await db.refresh(obj)
    return obj


async def get_product(db: AsyncSession, product_id: uuid.UUID) -> Product | None:
    result = await db.execute(select(Product).where(Product.id == product_id, Product.deleted_at.is_(None)))
    return result.scalar_one_or_none()


async def list_products(db: AsyncSession, tenant_id: uuid.UUID, skip: int = 0, limit: int = 100) -> list[Product]:
    result = await db.execute(
        select(Product)
        .where(Product.tenant_id == tenant_id, Product.deleted_at.is_(None))
        .order_by(Product.name)
        .offset(skip)
        .limit(limit)
    )
    return list(result.scalars().all())


async def update_product(db: AsyncSession, product_id: uuid.UUID, data: ProductUpdate) -> Product | None:
    obj = await get_product(db, product_id)
    if not obj:
        return None
    for k, v in data.model_dump(exclude_none=True).items():
        setattr(obj, k, v)
    obj.version += 1
    await db.commit()
    await db.refresh(obj)
    return obj


async def delete_product(db: AsyncSession, product_id: uuid.UUID) -> bool:
    from datetime import datetime

    obj = await get_product(db, product_id)
    if not obj:
        return False
    obj.deleted_at = datetime.now(_tz.utc)
    await db.commit()
    return True


async def get_product_by_barcode(db: AsyncSession, code: str) -> Product | None:
    result = await db.execute(
        select(Product)
        .join(Barcode)
        .where(
            Barcode.code == code,
            Product.deleted_at.is_(None),
            Barcode.deleted_at.is_(None),
        )
    )
    return result.scalar_one_or_none()


async def get_product_by_plu(db: AsyncSession, tenant_id: uuid.UUID, plu: str) -> Product | None:
    result = await db.execute(
        select(Product).where(
            Product.tenant_id == tenant_id,
            Product.plu == plu,
            Product.deleted_at.is_(None),
        )
    )
    return result.scalar_one_or_none()


async def create_barcode(db: AsyncSession, data: BarcodeCreate) -> Barcode:
    obj = Barcode(**data.model_dump())
    db.add(obj)
    await db.commit()
    await db.refresh(obj)
    return obj


async def list_barcodes(db: AsyncSession, product_id: uuid.UUID) -> list[Barcode]:
    result = await db.execute(
        select(Barcode).where(Barcode.product_id == product_id, Barcode.deleted_at.is_(None))
    )
    return list(result.scalars().all())


async def create_price(db: AsyncSession, data: PriceCreate) -> Price:
    obj = Price(**data.model_dump())
    db.add(obj)
    await db.commit()
    await db.refresh(obj)
    return obj


async def list_prices(db: AsyncSession, product_id: uuid.UUID) -> list[Price]:
    result = await db.execute(
        select(Price)
        .where(Price.product_id == product_id, Price.deleted_at.is_(None))
        .order_by(Price.price_type)
    )
    return list(result.scalars().all())


async def update_price(db: AsyncSession, price_id: uuid.UUID, data: PriceUpdate) -> Price | None:
    result = await db.execute(select(Price).where(Price.id == price_id))
    obj = result.scalar_one_or_none()
    if not obj:
        return None
    for k, v in data.model_dump(exclude_none=True).items():
        setattr(obj, k, v)
    obj.version += 1
    await db.commit()
    await db.refresh(obj)
    return obj


async def import_products_csv(db: AsyncSession, tenant_id: uuid.UUID, csv_content: str) -> dict:
    """
    CSV columns: plu,name,vat_rate,unit,is_weighable,weight_grams,weight_tolerance_pct,age_restricted,min_age,allergens,description
    allergens: semicolon-separated
    """
    reader = csv.DictReader(io.StringIO(csv_content))
    created = 0
    updated = 0
    errors = []

    for i, row in enumerate(reader, start=2):
        try:
            plu = row["plu"].strip()
            existing = await get_product_by_plu(db, tenant_id, plu)
            data = {
                "tenant_id": tenant_id,
                "plu": plu,
                "name": row["name"].strip(),
                "vat_rate": Decimal(row.get("vat_rate", "22").strip() or "22"),
                "unit": row.get("unit", "piece").strip() or "piece",
                "is_weighable": row.get("is_weighable", "").strip().lower() in ("1", "true", "yes"),
                "weight_grams": int(row["weight_grams"]) if row.get("weight_grams", "").strip() else None,
                "weight_tolerance_pct": Decimal(row["weight_tolerance_pct"]) if row.get("weight_tolerance_pct", "").strip() else None,
                "age_restricted": row.get("age_restricted", "").strip().lower() in ("1", "true", "yes"),
                "min_age": int(row["min_age"]) if row.get("min_age", "").strip() else None,
                "allergens": [a.strip() for a in row.get("allergens", "").split(";") if a.strip()],
                "description": row.get("description", "").strip() or None,
            }
            if existing:
                for k, v in data.items():
                    if k not in ("tenant_id", "plu"):
                        setattr(existing, k, v)
                existing.version += 1
                updated += 1
            else:
                db.add(Product(**data))
                created += 1
        except Exception as e:
            errors.append({"row": i, "error": str(e)})

    await db.commit()
    return {"created": created, "updated": updated, "errors": errors}
