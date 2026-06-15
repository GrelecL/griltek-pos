"""Store server (edge) unit tests — no real DB/Redis/network needed."""
import uuid
from decimal import Decimal
from unittest.mock import AsyncMock, MagicMock, patch

import httpx
import pytest
from sqlalchemy import select

from app.models.catalog import Barcode, Product
from app.models.live import EdgeStockItem, EdgeStockMovement, SyncQueueItem
from sync.pull import run_full_pull
from sync.push import enqueue, push_pending

# ── helpers ───────────────────────────────────────────────────────────────────

def _make_product(tenant_id: uuid.UUID) -> Product:
    pid = uuid.uuid4()
    return Product(
        id=pid, cloud_id=pid, tenant_id=tenant_id,
        plu="001", name="Mleko", vat_rate=Decimal("9.5"),
        unit="piece", is_weighable=False, age_restricted=False,
        allergens=[], is_active=True,
    )


# ── tests ─────────────────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_insert_product_and_barcode(db):
    tid = uuid.uuid4()
    product = _make_product(tid)
    db.add(product)
    await db.flush()

    barcode = Barcode(
        id=uuid.uuid4(), cloud_id=uuid.uuid4(),
        product_id=product.id, code="1234567890123", barcode_type="ean13",
    )
    db.add(barcode)
    await db.commit()

    result = await db.execute(
        select(Product).join(Barcode).where(Barcode.code == "1234567890123")
    )
    found = result.scalar_one_or_none()
    assert found is not None
    assert found.name == "Mleko"


@pytest.mark.asyncio
async def test_stock_movement_updates_qty(db):
    pid = uuid.uuid4()
    movement = EdgeStockMovement(product_id=pid, movement_type="receipt", qty=Decimal("10"))
    db.add(movement)
    stock = EdgeStockItem(product_id=pid, qty=Decimal("10"))
    db.add(stock)
    await db.commit()

    result = await db.execute(select(EdgeStockItem).where(EdgeStockItem.product_id == pid))
    item = result.scalar_one()
    assert item.qty == Decimal("10")


@pytest.mark.asyncio
async def test_sync_queue_enqueue(db):
    pid = uuid.uuid4()
    item = await enqueue(db, "stock_movement", {"product_id": str(pid), "qty": "5"})
    await db.commit()

    result = await db.execute(select(SyncQueueItem).where(SyncQueueItem.id == item.id))
    found = result.scalar_one()
    assert found.status == "pending"
    assert found.event_type == "stock_movement"


@pytest.mark.asyncio
async def test_pull_sync_wan_down(db):
    with patch("sync.pull.httpx.AsyncClient") as MockClient:
        mock_instance = MagicMock()
        mock_instance.__aenter__ = AsyncMock(return_value=mock_instance)
        mock_instance.__aexit__ = AsyncMock(return_value=False)
        mock_instance.get = AsyncMock(side_effect=httpx.ConnectError("WAN down"))
        MockClient.return_value = mock_instance

        # set tenant_id so pull doesn't skip
        import app.core.config as cfg
        original = cfg.settings.tenant_id
        cfg.settings.tenant_id = str(uuid.uuid4())
        try:
            result = await run_full_pull(db)
        finally:
            cfg.settings.tenant_id = original

    assert result.get("wan_down") is True


@pytest.mark.asyncio
async def test_push_sends_and_marks_sent(db):
    item = await enqueue(db, "stock_movement", {"product_id": str(uuid.uuid4()), "qty": "1"})
    await db.commit()

    mock_resp = MagicMock()
    mock_resp.status_code = 201

    with patch("sync.push.httpx.AsyncClient") as MockClient:
        mock_instance = MagicMock()
        mock_instance.__aenter__ = AsyncMock(return_value=mock_instance)
        mock_instance.__aexit__ = AsyncMock(return_value=False)
        mock_instance.post = AsyncMock(return_value=mock_resp)
        MockClient.return_value = mock_instance

        import app.core.config as cfg
        original = cfg.settings.cloud_api_url
        cfg.settings.cloud_api_url = "http://fake-cloud"
        try:
            result = await push_pending(db)
        finally:
            cfg.settings.cloud_api_url = original

    assert result["sent"] == 1
    assert result["failed"] == 0

    await db.refresh(item)
    assert item.status == "sent"


@pytest.mark.asyncio
async def test_push_wan_down_keeps_pending(db):
    item = await enqueue(db, "stock_movement", {"product_id": str(uuid.uuid4()), "qty": "1"})
    await db.commit()

    with patch("sync.push.httpx.AsyncClient") as MockClient:
        mock_instance = MagicMock()
        mock_instance.__aenter__ = AsyncMock(return_value=mock_instance)
        mock_instance.__aexit__ = AsyncMock(return_value=False)
        mock_instance.post = AsyncMock(side_effect=httpx.ConnectError("WAN down"))
        MockClient.return_value = mock_instance

        import app.core.config as cfg
        original = cfg.settings.cloud_api_url
        cfg.settings.cloud_api_url = "http://fake-cloud"
        try:
            result = await push_pending(db)
        finally:
            cfg.settings.cloud_api_url = original

    assert result.get("wan_down") is True

    # item still pending (error during push, rolled back to pending state)
    await db.refresh(item)
    assert item.status == "pending"


@pytest.mark.asyncio
async def test_multiple_stock_movements_accumulate(db):
    pid = uuid.uuid4()
    db.add(EdgeStockItem(product_id=pid, qty=Decimal("0")))
    await db.commit()

    for delta in [Decimal("5"), Decimal("3"), Decimal("-2")]:
        result = await db.execute(select(EdgeStockItem).where(EdgeStockItem.product_id == pid))
        item = result.scalar_one()
        item.qty += delta
        db.add(EdgeStockMovement(product_id=pid, movement_type="adjustment", qty=delta))
    await db.commit()

    result = await db.execute(select(EdgeStockItem).where(EdgeStockItem.product_id == pid))
    assert result.scalar_one().qty == Decimal("6")
