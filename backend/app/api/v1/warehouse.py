import uuid

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession

import app.services.warehouse as svc
from app.core.db import get_db
from app.schemas.warehouse import (
    StockItemRead,
    StockMovementCreate,
    StockMovementRead,
    WarehouseCreate,
    WarehouseRead,
)

router = APIRouter(prefix="/warehouse", tags=["warehouse"])


@router.post("/warehouses", response_model=WarehouseRead, status_code=201)
async def create_warehouse(data: WarehouseCreate, db: AsyncSession = Depends(get_db)):
    return await svc.create_warehouse(db, data)


@router.get("/warehouses", response_model=list[WarehouseRead])
async def list_warehouses(tenant_id: uuid.UUID = Query(...), db: AsyncSession = Depends(get_db)):
    return await svc.list_warehouses(db, tenant_id)


@router.get("/warehouses/{warehouse_id}", response_model=WarehouseRead)
async def get_warehouse(warehouse_id: uuid.UUID, db: AsyncSession = Depends(get_db)):
    obj = await svc.get_warehouse(db, warehouse_id)
    if not obj:
        raise HTTPException(404, "Warehouse not found")
    return obj


@router.get("/stock", response_model=list[StockItemRead])
async def list_stock(
    warehouse_id: uuid.UUID | None = Query(None),
    db: AsyncSession = Depends(get_db),
):
    return await svc.list_stock(db, warehouse_id=warehouse_id)


@router.post("/movements", response_model=StockMovementRead, status_code=201)
async def create_movement(data: StockMovementCreate, db: AsyncSession = Depends(get_db)):
    return await svc.create_movement(db, data)


@router.get("/movements", response_model=list[StockMovementRead])
async def list_movements(
    product_id: uuid.UUID | None = Query(None),
    warehouse_id: uuid.UUID | None = Query(None),
    limit: int = Query(100, le=500),
    db: AsyncSession = Depends(get_db),
):
    return await svc.list_movements(db, product_id, warehouse_id, limit)
