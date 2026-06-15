"""Gift card service: issue, validate, redeem, refund, top-up."""
import secrets
import uuid
from datetime import datetime, timezone
from decimal import Decimal

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.payments import GiftCard, GiftCardTransaction


def _now() -> datetime:
    return datetime.now(timezone.utc)


def generate_code() -> str:
    """16-char alphanumeric code in groups of 4: XXXX-XXXX-XXXX-XXXX."""
    raw = secrets.token_hex(8).upper()
    return f"{raw[0:4]}-{raw[4:8]}-{raw[8:12]}-{raw[12:16]}"


async def issue(
    db: AsyncSession,
    tenant_id: uuid.UUID,
    amount: Decimal,
    valid_until: datetime | None = None,
    issued_to: str | None = None,
    code: str | None = None,
) -> GiftCard:
    card = GiftCard(
        id=uuid.uuid4(),
        tenant_id=tenant_id,
        code=code or generate_code(),
        initial_balance=amount,
        balance=amount,
        status="active",
        valid_until=valid_until,
        issued_to=issued_to,
    )
    db.add(card)
    db.add(GiftCardTransaction(
        id=uuid.uuid4(),
        gift_card_id=card.id,
        transaction_type="issue",
        amount=amount,
        balance_before=Decimal("0"),
        balance_after=amount,
    ))
    await db.flush()
    return card


async def get_by_code(db: AsyncSession, code: str) -> GiftCard | None:
    result = await db.execute(select(GiftCard).where(GiftCard.code == code))
    return result.scalar_one_or_none()


async def validate(card: GiftCard) -> str | None:
    """Return error string if card cannot be used, None if OK."""
    if card.status != "active":
        return f"Gift card status: {card.status}"
    if card.balance <= Decimal("0"):
        return "Gift card balance is zero"
    if card.valid_until and card.valid_until < _now():
        return "Gift card has expired"
    return None


async def redeem(
    db: AsyncSession,
    card: GiftCard,
    amount: Decimal,
    sale_id: uuid.UUID | None = None,
) -> Decimal:
    """Redeem up to `amount` from card. Returns actual amount charged."""
    err = await validate(card)
    if err:
        raise ValueError(err)
    actual = min(card.balance, amount)
    balance_before = card.balance
    card.balance -= actual
    if card.balance == Decimal("0"):
        card.status = "redeemed"
    db.add(GiftCardTransaction(
        id=uuid.uuid4(),
        gift_card_id=card.id,
        transaction_type="redeem",
        amount=actual,
        balance_before=balance_before,
        balance_after=card.balance,
        sale_id=sale_id,
    ))
    return actual


async def refund(
    db: AsyncSession,
    card: GiftCard,
    amount: Decimal,
    sale_id: uuid.UUID | None = None,
) -> None:
    balance_before = card.balance
    card.balance += amount
    card.status = "active"
    db.add(GiftCardTransaction(
        id=uuid.uuid4(),
        gift_card_id=card.id,
        transaction_type="refund",
        amount=amount,
        balance_before=balance_before,
        balance_after=card.balance,
        sale_id=sale_id,
    ))


async def topup(
    db: AsyncSession,
    card: GiftCard,
    amount: Decimal,
) -> None:
    balance_before = card.balance
    card.balance += amount
    card.status = "active"
    db.add(GiftCardTransaction(
        id=uuid.uuid4(),
        gift_card_id=card.id,
        transaction_type="topup",
        amount=amount,
        balance_before=balance_before,
        balance_after=card.balance,
    ))
