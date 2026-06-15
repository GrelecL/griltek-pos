"""Payments API: gift cards, loyalty, credit, split payment."""
import uuid
from datetime import datetime
from decimal import Decimal
from typing import Any

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.db import get_db
from app.models.payments import LoyaltyProgram
from app.models.pos import Sale
from app.services import credit as credit_svc
from app.services import gift_card as gc_svc
from app.services import loyalty as loyalty_svc
from app.services.split_payment import process_split_payments

router = APIRouter(prefix="/payments", tags=["payments"])


# ── Gift cards ────────────────────────────────────────────────────────────────

class GiftCardIssueRequest(BaseModel):
    tenant_id: uuid.UUID
    amount: Decimal
    valid_until: datetime | None = None
    issued_to: str | None = None
    code: str | None = None


@router.post("/gift-cards", status_code=201)
async def issue_gift_card(body: GiftCardIssueRequest, db: AsyncSession = Depends(get_db)):
    card = await gc_svc.issue(
        db, body.tenant_id, body.amount,
        valid_until=body.valid_until, issued_to=body.issued_to, code=body.code,
    )
    await db.commit()
    return {"id": str(card.id), "code": card.code, "balance": str(card.balance), "status": card.status}


@router.get("/gift-cards/{code}")
async def get_gift_card(code: str, db: AsyncSession = Depends(get_db)):
    card = await gc_svc.get_by_code(db, code)
    if not card:
        raise HTTPException(404, "Gift card not found")
    err = await gc_svc.validate(card)
    return {
        "id": str(card.id), "code": card.code,
        "balance": str(card.balance), "status": card.status,
        "valid_until": card.valid_until.isoformat() if card.valid_until else None,
        "error": err,
    }


class TopupRequest(BaseModel):
    amount: Decimal


@router.post("/gift-cards/{code}/topup")
async def topup_gift_card(code: str, body: TopupRequest, db: AsyncSession = Depends(get_db)):
    card = await gc_svc.get_by_code(db, code)
    if not card:
        raise HTTPException(404, "Gift card not found")
    await gc_svc.topup(db, card, body.amount)
    await db.commit()
    return {"code": card.code, "balance": str(card.balance)}


# ── Loyalty ───────────────────────────────────────────────────────────────────

class LoyaltyProgramCreate(BaseModel):
    tenant_id: uuid.UUID
    name: str
    earn_rate: Decimal = Decimal("1.0")
    redeem_rate: Decimal = Decimal("0.01")
    min_redeem_points: int = 100
    tiers: list[dict[str, Any]] = []


@router.post("/loyalty/programs", status_code=201)
async def create_loyalty_program(body: LoyaltyProgramCreate, db: AsyncSession = Depends(get_db)):
    prog = LoyaltyProgram(id=uuid.uuid4(), **body.model_dump())
    db.add(prog)
    await db.commit()
    return {"id": str(prog.id), "name": prog.name}


@router.get("/loyalty/account/{customer_id}")
async def get_loyalty_account(customer_id: uuid.UUID, tenant_id: uuid.UUID, db: AsyncSession = Depends(get_db)):
    program = await loyalty_svc.get_program(db, tenant_id)
    if not program:
        raise HTTPException(404, "No active loyalty programme")
    account = await loyalty_svc.get_or_create_account(db, program.id, customer_id)
    await db.commit()
    return {
        "id": str(account.id), "customer_id": str(customer_id),
        "points_balance": account.points_balance,
        "points_lifetime": account.points_lifetime,
        "tier": account.tier,
        "redeem_value": str(Decimal(str(account.points_balance)) * program.redeem_rate),
    }


# ── Credit ────────────────────────────────────────────────────────────────────

@router.get("/credit/{customer_id}")
async def get_credit(customer_id: uuid.UUID, db: AsyncSession = Depends(get_db)):
    account = await credit_svc.get_credit_account(db, customer_id)
    if not account:
        raise HTTPException(404, "Credit account not found")
    return {
        "id": str(account.id), "customer_id": str(customer_id),
        "balance": str(account.balance),
        "credit_limit": str(account.credit_limit),
        "available": str(account.credit_limit - account.balance),
        "is_active": account.is_active,
    }


class SettlementRequest(BaseModel):
    amount: Decimal
    note: str | None = None


@router.post("/credit/{customer_id}/settle")
async def settle_credit(customer_id: uuid.UUID, body: SettlementRequest, db: AsyncSession = Depends(get_db)):
    account = await credit_svc.get_credit_account(db, customer_id)
    if not account:
        raise HTTPException(404, "Credit account not found")
    await credit_svc.settle(db, account, body.amount, note=body.note)
    await db.commit()
    return {"balance": str(account.balance)}


# ── Split payment ─────────────────────────────────────────────────────────────

class SplitPaymentRequest(BaseModel):
    sale_id: uuid.UUID
    customer_id: uuid.UUID | None = None
    tenant_id: uuid.UUID | None = None
    payments: list[dict[str, Any]]


@router.post("/split")
async def split_payment(body: SplitPaymentRequest, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(Sale).where(Sale.id == body.sale_id))
    sale = result.scalar_one_or_none()
    if not sale:
        raise HTTPException(404, "Sale not found")

    try:
        payment_rows = await process_split_payments(
            db, body.sale_id, sale.total,
            body.payments,
            customer_id=body.customer_id,
            tenant_id=body.tenant_id,
        )
    except ValueError as e:
        raise HTTPException(400, str(e))

    await db.commit()
    return {"processed": len(payment_rows), "sale_id": str(body.sale_id)}
