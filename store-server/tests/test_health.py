from unittest.mock import AsyncMock

import pytest
from httpx import ASGITransport, AsyncClient

from app.core.db import get_db
from app.core.redis import get_redis
from app.main import app


@pytest.mark.asyncio
async def test_root():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        resp = await client.get("/")
    assert resp.status_code == 200
    assert resp.json()["name"] == "Griltek POS Store Server"


@pytest.mark.asyncio
async def test_health_mocked():
    mock_db = AsyncMock()
    mock_db.execute = AsyncMock()
    mock_redis = AsyncMock()
    mock_redis.ping = AsyncMock()

    async def override_get_db():
        yield mock_db

    async def override_get_redis():
        return mock_redis

    app.dependency_overrides[get_db] = override_get_db
    app.dependency_overrides[get_redis] = override_get_redis
    try:
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            resp = await client.get("/api/v1/health")
        assert resp.status_code == 200
        assert resp.json()["status"] == "ok"
        assert resp.json()["service"] == "griltek-pos-edge"
    finally:
        app.dependency_overrides.clear()
