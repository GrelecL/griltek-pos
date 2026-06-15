from fastapi import APIRouter, Depends
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.db import get_db
from app.core.redis import get_redis

router = APIRouter()


@router.get("/health")
async def health(db: AsyncSession = Depends(get_db), redis=Depends(get_redis)):
    await db.execute(text("SELECT 1"))
    await redis.ping()
    return {"status": "ok", "service": "griltek-pos-edge"}
