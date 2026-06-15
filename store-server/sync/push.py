"""Push sync: send queued events to cloud API. Idempotent by item UUID."""
from datetime import datetime, timezone

import httpx
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.models.live import SyncQueueItem


def _endpoint_for(event_type: str) -> str:
    return {
        "stock_movement": "/warehouse/movements",
        "sale": "/sales",
        "fiscal_record": "/fiscal/fiscalize",
        "cash_session": "/cash-sessions",
    }.get(event_type, "/sync/events")


async def enqueue(db: AsyncSession, event_type: str, payload: dict) -> SyncQueueItem:
    item = SyncQueueItem(event_type=event_type, payload=payload)
    db.add(item)
    await db.flush()
    return item


async def push_pending(db: AsyncSession) -> dict:
    if not settings.cloud_api_url:
        return {"skipped": True, "reason": "cloud_api_url not configured"}

    result = await db.execute(
        select(SyncQueueItem)
        .where(SyncQueueItem.status == "pending")
        .order_by(SyncQueueItem.created_at)
        .limit(settings.sync_push_batch_size)
    )
    items = list(result.scalars().all())
    if not items:
        return {"sent": 0, "failed": 0}

    sent = 0
    failed = 0
    try:
        async with httpx.AsyncClient(base_url=settings.cloud_api_url, timeout=15.0) as client:
            for item in items:
                item.attempts += 1
                item.last_attempted_at = datetime.now(timezone.utc)
                try:
                    resp = await client.post(_endpoint_for(item.event_type), json=item.payload)
                    if resp.status_code in (200, 201, 409):
                        item.status = "sent"
                        sent += 1
                    else:
                        item.status = "failed"
                        item.error = f"HTTP {resp.status_code}"
                        failed += 1
                except httpx.RequestError as e:
                    item.error = str(e)[:200]
                    failed += 1
                    await db.commit()
                    return {"sent": sent, "failed": failed, "wan_down": True}
    except httpx.RequestError as e:
        return {"sent": sent, "failed": failed, "wan_down": True, "error": str(e)}

    await db.commit()
    return {"sent": sent, "failed": failed}
