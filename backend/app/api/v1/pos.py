import uuid

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession

import app.services.pos as svc
from app.core.db import get_db
from app.schemas.pos import (
    CashAdjustment,
    CashSessionClose,
    CashSessionOpen,
    CashSessionRead,
    SaleCreate,
    SaleRead,
    XReport,
    ZReport,
)

router = APIRouter(tags=["pos"])


@router.post("/cash-sessions", response_model=CashSessionRead, status_code=201)
async def open_session(data: CashSessionOpen, db: AsyncSession = Depends(get_db)):
    return await svc.open_session(db, data)


@router.get("/cash-sessions/{session_id}", response_model=CashSessionRead)
async def get_session(session_id: uuid.UUID, db: AsyncSession = Depends(get_db)):
    obj = await svc.get_session(db, session_id)
    if not obj:
        raise HTTPException(404, "Session not found")
    return obj


@router.post("/cash-sessions/{session_id}/cash-in", response_model=CashSessionRead)
async def cash_in(
    session_id: uuid.UUID,
    data: CashAdjustment,
    db: AsyncSession = Depends(get_db),
):
    obj = await svc.cash_in(db, session_id, data)
    if not obj:
        raise HTTPException(400, "Session not open")
    return obj


@router.post("/cash-sessions/{session_id}/cash-out", response_model=CashSessionRead)
async def cash_out(
    session_id: uuid.UUID,
    data: CashAdjustment,
    db: AsyncSession = Depends(get_db),
):
    obj = await svc.cash_out(db, session_id, data)
    if not obj:
        raise HTTPException(400, "Session not open")
    return obj


@router.post("/cash-sessions/{session_id}/close", response_model=CashSessionRead)
async def close_session(
    session_id: uuid.UUID,
    data: CashSessionClose,
    db: AsyncSession = Depends(get_db),
):
    obj = await svc.close_session(db, session_id, data)
    if not obj:
        raise HTTPException(400, "Session not open")
    return obj


@router.get("/cash-sessions/{session_id}/x-report", response_model=XReport)
async def x_report(session_id: uuid.UUID, db: AsyncSession = Depends(get_db)):
    obj = await svc.x_report(db, session_id)
    if not obj:
        raise HTTPException(404, "Session not found")
    return obj


@router.get("/cash-sessions/{session_id}/z-report", response_model=ZReport)
async def z_report(session_id: uuid.UUID, db: AsyncSession = Depends(get_db)):
    obj = await svc.z_report(db, session_id)
    if not obj:
        raise HTTPException(400, "Session must be closed for Z-report")
    return obj


@router.post("/sales", response_model=SaleRead, status_code=201)
async def create_sale(data: SaleCreate, db: AsyncSession = Depends(get_db)):
    return await svc.create_sale(db, data)


@router.get("/sales", response_model=list[SaleRead])
async def list_sales(
    location_id: uuid.UUID | None = Query(None),
    session_id: uuid.UUID | None = Query(None),
    limit: int = Query(100, le=500),
    db: AsyncSession = Depends(get_db),
):
    return await svc.list_sales(db, location_id, session_id, limit)


@router.get("/sales/{sale_id}", response_model=SaleRead)
async def get_sale(sale_id: uuid.UUID, db: AsyncSession = Depends(get_db)):
    obj = await svc.get_sale(db, sale_id)
    if not obj:
        raise HTTPException(404, "Sale not found")
    return obj


@router.post("/sales/{sale_id}/void", response_model=SaleRead)
async def void_sale(
    sale_id: uuid.UUID,
    user_id: uuid.UUID = Query(...),
    db: AsyncSession = Depends(get_db),
):
    obj = await svc.void_sale(db, sale_id, user_id)
    if not obj:
        raise HTTPException(400, "Cannot void this sale")
    return obj
