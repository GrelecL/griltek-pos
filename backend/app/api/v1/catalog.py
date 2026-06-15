import uuid

from fastapi import APIRouter, Depends, File, HTTPException, Query, UploadFile
from sqlalchemy.ext.asyncio import AsyncSession

import app.services.catalog as svc
from app.core.db import get_db
from app.schemas.catalog import (
    BarcodeCreate,
    BarcodeRead,
    CategoryCreate,
    CategoryRead,
    CategoryUpdate,
    PriceCreate,
    PriceRead,
    PriceUpdate,
    ProductCreate,
    ProductRead,
    ProductUpdate,
)

router = APIRouter(prefix="/catalog", tags=["catalog"])


@router.post("/categories", response_model=CategoryRead, status_code=201)
async def create_category(data: CategoryCreate, db: AsyncSession = Depends(get_db)):
    return await svc.create_category(db, data)


@router.get("/categories", response_model=list[CategoryRead])
async def list_categories(tenant_id: uuid.UUID = Query(...), db: AsyncSession = Depends(get_db)):
    return await svc.list_categories(db, tenant_id)


@router.get("/categories/{category_id}", response_model=CategoryRead)
async def get_category(category_id: uuid.UUID, db: AsyncSession = Depends(get_db)):
    obj = await svc.get_category(db, category_id)
    if not obj:
        raise HTTPException(404, "Category not found")
    return obj


@router.patch("/categories/{category_id}", response_model=CategoryRead)
async def update_category(category_id: uuid.UUID, data: CategoryUpdate, db: AsyncSession = Depends(get_db)):
    obj = await svc.update_category(db, category_id, data)
    if not obj:
        raise HTTPException(404, "Category not found")
    return obj


@router.delete("/categories/{category_id}", status_code=204)
async def delete_category(category_id: uuid.UUID, db: AsyncSession = Depends(get_db)):
    if not await svc.delete_category(db, category_id):
        raise HTTPException(404, "Category not found")


@router.post("/products/import", response_model=dict)
async def import_products(
    tenant_id: uuid.UUID = Query(...),
    file: UploadFile = File(...),
    db: AsyncSession = Depends(get_db),
):
    content = (await file.read()).decode("utf-8")
    return await svc.import_products_csv(db, tenant_id, content)


@router.get("/products/by-barcode/{code}", response_model=ProductRead)
async def get_by_barcode(code: str, db: AsyncSession = Depends(get_db)):
    obj = await svc.get_product_by_barcode(db, code)
    if not obj:
        raise HTTPException(404, "Product not found")
    return obj


@router.get("/products/by-plu/{plu}", response_model=ProductRead)
async def get_by_plu(plu: str, tenant_id: uuid.UUID = Query(...), db: AsyncSession = Depends(get_db)):
    obj = await svc.get_product_by_plu(db, tenant_id, plu)
    if not obj:
        raise HTTPException(404, "Product not found")
    return obj


@router.post("/products", response_model=ProductRead, status_code=201)
async def create_product(data: ProductCreate, db: AsyncSession = Depends(get_db)):
    return await svc.create_product(db, data)


@router.get("/products", response_model=list[ProductRead])
async def list_products(
    tenant_id: uuid.UUID = Query(...),
    skip: int = 0,
    limit: int = 100,
    db: AsyncSession = Depends(get_db),
):
    return await svc.list_products(db, tenant_id, skip, limit)


@router.get("/products/{product_id}", response_model=ProductRead)
async def get_product(product_id: uuid.UUID, db: AsyncSession = Depends(get_db)):
    obj = await svc.get_product(db, product_id)
    if not obj:
        raise HTTPException(404, "Product not found")
    return obj


@router.patch("/products/{product_id}", response_model=ProductRead)
async def update_product(product_id: uuid.UUID, data: ProductUpdate, db: AsyncSession = Depends(get_db)):
    obj = await svc.update_product(db, product_id, data)
    if not obj:
        raise HTTPException(404, "Product not found")
    return obj


@router.delete("/products/{product_id}", status_code=204)
async def delete_product(product_id: uuid.UUID, db: AsyncSession = Depends(get_db)):
    if not await svc.delete_product(db, product_id):
        raise HTTPException(404, "Product not found")


@router.post("/products/{product_id}/barcodes", response_model=BarcodeRead, status_code=201)
async def create_barcode(product_id: uuid.UUID, data: BarcodeCreate, db: AsyncSession = Depends(get_db)):
    data.product_id = product_id
    return await svc.create_barcode(db, data)


@router.get("/products/{product_id}/barcodes", response_model=list[BarcodeRead])
async def list_barcodes(product_id: uuid.UUID, db: AsyncSession = Depends(get_db)):
    return await svc.list_barcodes(db, product_id)


@router.post("/products/{product_id}/prices", response_model=PriceRead, status_code=201)
async def create_price(product_id: uuid.UUID, data: PriceCreate, db: AsyncSession = Depends(get_db)):
    data.product_id = product_id
    return await svc.create_price(db, data)


@router.get("/products/{product_id}/prices", response_model=list[PriceRead])
async def list_prices(product_id: uuid.UUID, db: AsyncSession = Depends(get_db)):
    return await svc.list_prices(db, product_id)


@router.patch("/prices/{price_id}", response_model=PriceRead)
async def update_price(price_id: uuid.UUID, data: PriceUpdate, db: AsyncSession = Depends(get_db)):
    obj = await svc.update_price(db, price_id, data)
    if not obj:
        raise HTTPException(404, "Price not found")
    return obj
