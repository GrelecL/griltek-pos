import uuid

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.warehouse import StockItem, StockMovement, Warehouse
from app.schemas.warehouse import StockMovementCreate, WarehouseCreate


async def create_warehouse(db: AsyncSession, data: WarehouseCreate) -> Warehouse:
    obj = Warehouse(**data.model_dump())
    db.add(obj)
    await db.commit()
    await db.refresh(obj)
    return obj


async def get_warehouse(db: AsyncSession, warehouse_id: uuid.UUID) -> Warehouse | None:
    result = await db.execute(
        select(Warehouse).where(Warehouse.id == warehouse_id, Warehouse.deleted_at.is_(None))
    )
    return result.scalar_one_or_none()


async def list_warehouses(db: AsyncSession, tenant_id: uuid.UUID) -> list[Warehouse]:
    result = await db.execute(
        select(Warehouse)
        .where(Warehouse.tenant_id == tenant_id, Warehouse.deleted_at.is_(None))
        .order_by(Warehouse.name)
    )
    return list(result.scalars().all())


async def get_stock_item(db: AsyncSession, product_id: uuid.UUID, warehouse_id: uuid.UUID) -> StockItem | None:
    result = await db.execute(
        select(StockItem).where(StockItem.product_id == product_id, StockItem.warehouse_id == warehouse_id)
    )
    return result.scalar_one_or_none()


async def list_stock(
    db: AsyncSession,
    warehouse_id: uuid.UUID | None = None,
    tenant_id: uuid.UUID | None = None,
) -> list[StockItem]:
    q = select(StockItem)
    if warehouse_id:
        q = q.where(StockItem.warehouse_id == warehouse_id)
    result = await db.execute(q)
    return list(result.scalars().all())


async def create_movement(db: AsyncSession, data: StockMovementCreate) -> StockMovement:
    """Append a stock movement and update the running qty on StockItem."""
    movement = StockMovement(**data.model_dump())
    db.add(movement)

    # upsert StockItem running qty
    stock_item = await get_stock_item(db, data.product_id, data.warehouse_id)
    if stock_item:
        stock_item.qty += data.qty
        stock_item.version += 1
    else:
        stock_item = StockItem(
            product_id=data.product_id,
            warehouse_id=data.warehouse_id,
            qty=data.qty,
        )
        db.add(stock_item)

    await db.commit()
    await db.refresh(movement)
    return movement


async def list_movements(
    db: AsyncSession,
    product_id: uuid.UUID | None = None,
    warehouse_id: uuid.UUID | None = None,
    limit: int = 100,
) -> list[StockMovement]:
    q = select(StockMovement)
    if product_id:
        q = q.where(StockMovement.product_id == product_id)
    if warehouse_id:
        q = q.where(StockMovement.warehouse_id == warehouse_id)
    q = q.order_by(StockMovement.occurred_at.desc()).limit(limit)
    result = await db.execute(q)
    return list(result.scalars().all())
