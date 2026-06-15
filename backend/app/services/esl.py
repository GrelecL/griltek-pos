"""ESL service: device registration, label sync."""
from __future__ import annotations

import uuid
from datetime import datetime, timezone
from decimal import Decimal

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.adapters.esl.adapter import ESLLabelData, get_esl_adapter
from app.models.catalog import Product
from app.models.esl import ESLDevice
from app.services.pricing import compute_price, get_base_price


async def register_device(
    db: AsyncSession,
    location_id: uuid.UUID,
    esl_id: str,
    product_id: uuid.UUID | None = None,
) -> ESLDevice:
    device = ESLDevice(
        id=uuid.uuid4(),
        location_id=location_id,
        esl_id=esl_id,
        product_id=product_id,
        status="pending",
    )
    db.add(device)
    await db.flush()
    return device


async def list_devices(db: AsyncSession, location_id: uuid.UUID) -> list[ESLDevice]:
    result = await db.execute(
        select(ESLDevice).where(ESLDevice.location_id == location_id)
    )
    return list(result.scalars().all())


async def assign_product(
    db: AsyncSession, device_id: uuid.UUID, product_id: uuid.UUID
) -> ESLDevice:
    result = await db.execute(select(ESLDevice).where(ESLDevice.id == device_id))
    device = result.scalar_one_or_none()
    if not device:
        raise ValueError("ESL device not found")
    device.product_id = product_id
    device.status = "pending"
    return device


async def sync_device(
    db: AsyncSession,
    device_id: uuid.UUID,
    tenant_id: uuid.UUID,
) -> ESLDevice:
    """Push current price + promo info to a single ESL unit."""
    result = await db.execute(select(ESLDevice).where(ESLDevice.id == device_id))
    device = result.scalar_one_or_none()
    if not device:
        raise ValueError("ESL device not found")
    if not device.product_id:
        raise ValueError("ESL device has no linked product")

    prod_result = await db.execute(select(Product).where(Product.id == device.product_id))
    product = prod_result.scalar_one_or_none()
    if not product:
        raise ValueError("Linked product not found")

    base_price = await get_base_price(
        db, product.id, Decimal("1"), location_id=device.location_id
    )
    if base_price is None:
        device.status = "error"
        device.last_error = "No active price found for product"
        return device

    price_result = await compute_price(
        db, product.id, base_price, Decimal("1"),
        tenant_id=tenant_id,
        category_id=product.category_id,
    )

    promo_label = " | ".join(price_result.applied_rules) if price_result.applied_rules else None
    label = ESLLabelData(
        esl_id=device.esl_id,
        product_name=product.name,
        plu=product.plu,
        price=price_result.final_price,
        original_price=base_price if price_result.discount_amount > 0 else None,
        promo_label=promo_label,
    )

    adapter = get_esl_adapter()
    push_result = await adapter.push(label)

    now = datetime.now(timezone.utc)
    if push_result.success:
        device.status = "synced"
        device.last_synced_at = now
        device.last_price = price_result.final_price
        device.last_error = None
    else:
        device.status = "error"
        device.last_error = push_result.error

    return device


async def sync_location(
    db: AsyncSession,
    location_id: uuid.UUID,
    tenant_id: uuid.UUID,
) -> dict:
    """Sync all ESL devices at a location. Returns summary dict."""
    devices = await list_devices(db, location_id)
    synced = errors = skipped = 0
    for device in devices:
        if not device.product_id:
            skipped += 1
            continue
        try:
            await sync_device(db, device.id, tenant_id)
            synced += 1
        except Exception as exc:
            device.status = "error"
            device.last_error = str(exc)
            errors += 1
    return {"synced": synced, "errors": errors, "skipped": skipped, "total": len(devices)}
