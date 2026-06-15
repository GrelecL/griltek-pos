"""Device heartbeat — devices ping edge to report alive status."""
from datetime import datetime, timezone

from fastapi import APIRouter, Depends

from app.core.redis import get_redis

router = APIRouter(prefix="/heartbeat", tags=["heartbeat"])
DEVICE_TTL = 120  # seconds


@router.post("/device/{device_id}")
async def device_heartbeat(device_id: str, redis=Depends(get_redis)):
    key = f"device_online:{device_id}"
    await redis.set(key, datetime.now(timezone.utc).isoformat(), ex=DEVICE_TTL)
    return {"status": "ok", "device_id": device_id}


@router.get("/devices")
async def list_devices(redis=Depends(get_redis)):
    keys = await redis.keys("device_online:*")
    devices = []
    for k in keys:
        val = await redis.get(k)
        device_id = k.replace("device_online:", "")
        devices.append({"device_id": device_id, "last_seen": val})
    return {"devices": devices}
