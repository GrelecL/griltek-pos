"""Hospitality API: floor areas, tables, orders, KDS, materialise."""
import uuid
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, WebSocket, WebSocketDisconnect
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.db import get_db
from app.services.hospitality import (
    FloorAreaCreate,
    OrderCreate,
    OrderLineCreate,
    TableCreate,
    add_order_lines,
    create_floor_area,
    create_order,
    create_table,
    fire_course,
    get_kds_lines,
    get_order,
    list_open_orders,
    list_tables,
    materialise_order,
    set_table_status,
    update_kds_status,
)

router = APIRouter(prefix="/hospitality", tags=["hospitality"])


# ── simple serialisers ────────────────────────────────────────────────────────

def _area_out(a) -> dict:
    return {"id": str(a.id), "location_id": str(a.location_id), "name": a.name, "sort_order": a.sort_order}


def _table_out(t) -> dict:
    return {
        "id": str(t.id), "floor_area_id": str(t.floor_area_id),
        "number": t.number, "capacity": t.capacity,
        "status": t.status, "pos_x": t.pos_x, "pos_y": t.pos_y,
    }


def _line_out(l) -> dict:
    return {
        "id": str(l.id), "order_id": str(l.order_id),
        "product_id": str(l.product_id), "product_name": l.product_name,
        "plu": l.plu, "qty": str(l.qty), "unit_price": str(l.unit_price),
        "vat_rate": str(l.vat_rate), "line_total": str(l.line_total),
        "course": l.course, "kds_status": l.kds_status,
        "kds_station": l.kds_station, "note": l.note, "modifiers": l.modifiers,
        "fired_at": l.fired_at.isoformat() if l.fired_at else None,
        "ready_at": l.ready_at.isoformat() if l.ready_at else None,
    }


def _order_out(o) -> dict:
    return {
        "id": str(o.id), "location_id": str(o.location_id),
        "table_id": str(o.table_id) if o.table_id else None,
        "user_id": str(o.user_id), "status": o.status,
        "service_type": o.service_type, "covers": o.covers,
        "pager_number": o.pager_number, "note": o.note,
        "sale_id": str(o.sale_id) if o.sale_id else None,
        "lines": [_line_out(l) for l in o.lines] if o.lines else [],
        "created_at": o.created_at.isoformat() if o.created_at else None,
    }


# ── floor areas ───────────────────────────────────────────────────────────────

@router.post("/floor-areas", status_code=201)
async def api_create_floor_area(data: FloorAreaCreate, db: AsyncSession = Depends(get_db)):
    area = await create_floor_area(db, data)
    await db.commit()
    return _area_out(area)


# ── tables ────────────────────────────────────────────────────────────────────

@router.post("/tables", status_code=201)
async def api_create_table(data: TableCreate, db: AsyncSession = Depends(get_db)):
    table = await create_table(db, data)
    await db.commit()
    return _table_out(table)


@router.get("/tables")
async def api_list_tables(location_id: uuid.UUID, db: AsyncSession = Depends(get_db)):
    tables = await list_tables(db, location_id)
    return [_table_out(t) for t in tables]


class TableStatusUpdate(BaseModel):
    status: str


@router.patch("/tables/{table_id}/status")
async def api_set_table_status(
    table_id: uuid.UUID, body: TableStatusUpdate, db: AsyncSession = Depends(get_db)
):
    table = await set_table_status(db, table_id, body.status)
    if not table:
        raise HTTPException(404, "Table not found")
    await db.commit()
    return _table_out(table)


# ── orders ────────────────────────────────────────────────────────────────────

@router.post("/orders", status_code=201)
async def api_create_order(data: OrderCreate, db: AsyncSession = Depends(get_db)):
    order = await create_order(db, data)
    await db.commit()
    order = await get_order(db, order.id)
    return _order_out(order)


@router.get("/orders")
async def api_list_orders(location_id: uuid.UUID, db: AsyncSession = Depends(get_db)):
    orders = await list_open_orders(db, location_id)
    return [_order_out(o) for o in orders]


@router.get("/orders/{order_id}")
async def api_get_order(order_id: uuid.UUID, db: AsyncSession = Depends(get_db)):
    order = await get_order(db, order_id)
    if not order:
        raise HTTPException(404, "Order not found")
    return _order_out(order)


class AddLinesBody(BaseModel):
    lines: list[OrderLineCreate]


@router.post("/orders/{order_id}/lines", status_code=201)
async def api_add_lines(order_id: uuid.UUID, body: AddLinesBody, db: AsyncSession = Depends(get_db)):
    order = await add_order_lines(db, order_id, body.lines)
    if not order:
        raise HTTPException(404, "Order not found or already closed")
    await db.commit()
    order = await get_order(db, order_id)
    return _order_out(order)


class FireCourseBody(BaseModel):
    course: int


@router.post("/orders/{order_id}/fire-course")
async def api_fire_course(order_id: uuid.UUID, body: FireCourseBody, db: AsyncSession = Depends(get_db)):
    fired = await fire_course(db, order_id, body.course)
    await db.commit()
    return {"fired": fired}


class MaterialiseBody(BaseModel):
    cash_session_id: uuid.UUID
    user_id: uuid.UUID
    payments: list[dict[str, Any]]


@router.post("/orders/{order_id}/materialise", status_code=201)
async def api_materialise(order_id: uuid.UUID, body: MaterialiseBody, db: AsyncSession = Depends(get_db)):
    try:
        sale = await materialise_order(db, order_id, body.cash_session_id, body.user_id, body.payments)
    except ValueError as e:
        raise HTTPException(400, str(e))
    await db.commit()
    return {"sale_id": str(sale.id), "total": str(sale.total)}


# ── KDS ───────────────────────────────────────────────────────────────────────

@router.get("/kds/lines")
async def api_kds_lines(
    location_id: uuid.UUID,
    station: str | None = None,
    db: AsyncSession = Depends(get_db),
):
    lines = await get_kds_lines(db, location_id, station)
    return [_line_out(l) for l in lines]


class KDSStatusUpdate(BaseModel):
    status: str


@router.patch("/kds/lines/{line_id}/status")
async def api_kds_update_status(
    line_id: uuid.UUID, body: KDSStatusUpdate, db: AsyncSession = Depends(get_db)
):
    line = await update_kds_status(db, line_id, body.status)
    if not line:
        raise HTTPException(404, "Order line not found")
    await db.commit()
    return _line_out(line)


# ── KDS WebSocket ─────────────────────────────────────────────────────────────

class KDSConnectionManager:
    def __init__(self):
        self.active: list[WebSocket] = []

    async def connect(self, ws: WebSocket):
        await ws.accept()
        self.active.append(ws)

    def disconnect(self, ws: WebSocket):
        self.active.remove(ws)

    async def broadcast(self, message: dict):
        import json
        payload = json.dumps(message)
        for ws in list(self.active):
            try:
                await ws.send_text(payload)
            except Exception:
                self.active.remove(ws)


_manager = KDSConnectionManager()


@router.websocket("/kds/ws")
async def kds_websocket(ws: WebSocket, db: AsyncSession = Depends(get_db)):
    await _manager.connect(ws)
    try:
        while True:
            data = await ws.receive_json()
            # Client sends: {"action": "status_update", "line_id": "...", "status": "..."}
            if data.get("action") == "status_update":
                line_id = uuid.UUID(data["line_id"])
                line = await update_kds_status(db, line_id, data["status"])
                if line:
                    await db.commit()
                    await _manager.broadcast({"event": "line_updated", "line": _line_out(line)})
    except WebSocketDisconnect:
        _manager.disconnect(ws)
