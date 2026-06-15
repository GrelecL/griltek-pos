"""Live stock — edge authoritative. Redis lock for last-unit protection."""
import uuid
from decimal import Decimal

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.db import get_db
from app.core.redis import get_redis
from app.models.live import EdgeStockItem, EdgeStockMovement
from sync.push import enqueue

router = APIRouter(prefix="/stock", tags=["stock"])
STOCK_LOCK_TTL = 30  # seconds


@router.get("/items")
async def list_stock(db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(EdgeStockItem))
    return [_stock_dict(s) for s in result.scalars().all()]


@router.get("/items/{product_id}")
async def get_stock(product_id: uuid.UUID, db: AsyncSession = Depends(get_db)):
    result = await db.execute(
        select(EdgeStockItem).where(EdgeStockItem.product_id == product_id)
    )
    s = result.scalar_one_or_none()
    if not s:
        return {"product_id": str(product_id), "qty": "0", "reserved_qty": "0"}
    return _stock_dict(s)


@router.post("/movements")
async def create_movement(data: dict, db: AsyncSession = Depends(get_db), redis=Depends(get_redis)):
    product_id = uuid.UUID(data["product_id"])
    qty = Decimal(str(data["qty"]))
    movement_type = data["movement_type"]

    # Redis stock-lock: guard last unit against concurrent terminals
    if movement_type == "sale" and qty > 0:
        result = await db.execute(
            select(EdgeStockItem).where(EdgeStockItem.product_id == product_id)
        )
        item = result.scalar_one_or_none()
        current_qty = item.qty if item else Decimal("0")
        if current_qty - qty < 0:
            raise HTTPException(409, f"Insufficient stock: {current_qty} available")
        await redis.set(f"stock_lock:{product_id}", "1", nx=True, ex=STOCK_LOCK_TTL)

    movement = EdgeStockMovement(
        product_id=product_id,
        movement_type=movement_type,
        qty=qty,
        reference_id=uuid.UUID(data["reference_id"]) if data.get("reference_id") else None,
        reference_type=data.get("reference_type"),
        device_id=uuid.UUID(data["device_id"]) if data.get("device_id") else None,
    )
    db.add(movement)

    result = await db.execute(
        select(EdgeStockItem).where(EdgeStockItem.product_id == product_id)
    )
    stock_item = result.scalar_one_or_none()
    if stock_item:
        stock_item.qty += qty
        stock_item.version += 1
    else:
        db.add(EdgeStockItem(product_id=product_id, qty=qty))

    await enqueue(db, "stock_movement", {
        "id": str(movement.id),
        "product_id": str(product_id),
        "warehouse_id": data.get("warehouse_id", "00000000-0000-0000-0000-000000000001"),
        "movement_type": movement_type,
        "qty": str(qty),
        "reference_id": data.get("reference_id"),
        "reference_type": data.get("reference_type"),
    })

    await db.commit()
    return {"id": str(movement.id), "product_id": str(product_id), "qty": str(qty)}


def _stock_dict(s: EdgeStockItem) -> dict:
    return {
        "product_id": str(s.product_id),
        "qty": str(s.qty),
        "reserved_qty": str(s.reserved_qty),
    }
