"""Loyalty service: programme management, earn/redeem points, tier updates."""
import uuid
from decimal import Decimal

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.payments import LoyaltyAccount, LoyaltyProgram, LoyaltyTransaction


async def get_program(db: AsyncSession, tenant_id: uuid.UUID) -> LoyaltyProgram | None:
    result = await db.execute(
        select(LoyaltyProgram).where(LoyaltyProgram.tenant_id == tenant_id, LoyaltyProgram.is_active.is_(True))
    )
    return result.scalar_one_or_none()


async def get_or_create_account(
    db: AsyncSession,
    program_id: uuid.UUID,
    customer_id: uuid.UUID,
) -> LoyaltyAccount:
    result = await db.execute(
        select(LoyaltyAccount).where(
            LoyaltyAccount.program_id == program_id,
            LoyaltyAccount.customer_id == customer_id,
        )
    )
    account = result.scalar_one_or_none()
    if not account:
        account = LoyaltyAccount(
            id=uuid.uuid4(),
            program_id=program_id,
            customer_id=customer_id,
        )
        db.add(account)
        await db.flush()
    return account


def _compute_tier(tiers: list[dict], lifetime_points: int) -> str:
    """Return tier name based on lifetime points."""
    current = "standard"
    for tier in sorted(tiers, key=lambda t: t.get("min_points", 0)):
        if lifetime_points >= tier.get("min_points", 0):
            current = tier.get("name", "standard")
    return current


def _earn_multiplier(tiers: list[dict], tier_name: str) -> Decimal:
    for tier in tiers:
        if tier.get("name") == tier_name:
            return Decimal(str(tier.get("earn_multiplier", 1)))
    return Decimal("1")


async def earn_points(
    db: AsyncSession,
    program: LoyaltyProgram,
    account: LoyaltyAccount,
    sale_total: Decimal,
    sale_id: uuid.UUID | None = None,
) -> int:
    """Compute and credit earned points. Returns points earned."""
    multiplier = _earn_multiplier(program.tiers, account.tier)
    raw = sale_total * program.earn_rate * multiplier
    points = int(raw)
    if points <= 0:
        return 0

    balance_before = account.points_balance
    account.points_balance += points
    account.points_lifetime += points
    account.tier = _compute_tier(program.tiers, account.points_lifetime)

    db.add(LoyaltyTransaction(
        id=uuid.uuid4(),
        account_id=account.id,
        transaction_type="earn",
        points=points,
        balance_before=balance_before,
        balance_after=account.points_balance,
        sale_id=sale_id,
    ))
    return points


async def redeem_points(
    db: AsyncSession,
    program: LoyaltyProgram,
    account: LoyaltyAccount,
    points_to_redeem: int,
    sale_id: uuid.UUID | None = None,
) -> Decimal:
    """Redeem points from account. Returns euro value of redeemed points."""
    if not account.is_active:
        raise ValueError("Loyalty account is inactive")
    if points_to_redeem < program.min_redeem_points:
        raise ValueError(f"Minimum redemption is {program.min_redeem_points} points")
    if points_to_redeem > account.points_balance:
        raise ValueError(f"Insufficient points: have {account.points_balance}, need {points_to_redeem}")

    euro_value = Decimal(str(points_to_redeem)) * program.redeem_rate
    balance_before = account.points_balance
    account.points_balance -= points_to_redeem

    db.add(LoyaltyTransaction(
        id=uuid.uuid4(),
        account_id=account.id,
        transaction_type="redeem",
        points=-points_to_redeem,
        balance_before=balance_before,
        balance_after=account.points_balance,
        sale_id=sale_id,
    ))
    return euro_value.quantize(Decimal("0.01"))
