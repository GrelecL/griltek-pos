"""Sync management: trigger pull/push, check status."""
from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.db import get_db
from app.models.live import SyncCursorRecord, SyncQueueItem
from sync.pull import run_full_pull
from sync.push import push_pending

router = APIRouter(prefix="/sync", tags=["sync"])


@router.post("/pull")
async def trigger_pull(db: AsyncSession = Depends(get_db)):
    return await run_full_pull(db)


@router.post("/push")
async def trigger_push(db: AsyncSession = Depends(get_db)):
    return await push_pending(db)


@router.get("/status")
async def sync_status(db: AsyncSession = Depends(get_db)):
    cursors_result = await db.execute(select(SyncCursorRecord))
    cursors = [
        {
            "entity_type": c.entity_type,
            "pull_version": c.pull_version,
            "last_pulled_at": str(c.last_pulled_at),
        }
        for c in cursors_result.scalars().all()
    ]
    pending = await db.execute(select(SyncQueueItem).where(SyncQueueItem.status == "pending"))
    failed = await db.execute(select(SyncQueueItem).where(SyncQueueItem.status == "failed"))
    return {
        "location_id": settings.location_id,
        "cursors": cursors,
        "queue_pending": len(list(pending.scalars().all())),
        "queue_failed": len(list(failed.scalars().all())),
    }
