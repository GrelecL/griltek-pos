"""Credit account service: charge, settle, adjust."""
import uuid
from decimal import Decimal

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.customer import CreditAccount
from app.models.payments import CreditTransaction


async def get_credit_account(db: AsyncSession, customer_id: uuid.UUID) -> CreditAccount | None:
    result = await db.execute(
        select(CreditAccount).where(CreditAccount.customer_id == customer_id)
    )
    return result.scalar_one_or_none()


async def charge(
    db: AsyncSession,
    account: CreditAccount,
    amount: Decimal,
    sale_id: uuid.UUID | None = None,
    note: str | None = None,
) -> None:
    """Charge credit account (increases balance owed)."""
    if not account.is_active:
        raise ValueError("Credit account is inactive")
    new_balance = account.balance + amount
    if new_balance > account.credit_limit:
        raise ValueError(
            f"Credit limit exceeded: limit {account.credit_limit}, "
            f"current {account.balance}, charge {amount}"
        )
    balance_before = account.balance
    account.balance = new_balance
    db.add(CreditTransaction(
        id=uuid.uuid4(),
        credit_account_id=account.id,
        transaction_type="charge",
        amount=amount,
        balance_before=balance_before,
        balance_after=account.balance,
        sale_id=sale_id,
        note=note,
    ))


async def settle(
    db: AsyncSession,
    account: CreditAccount,
    amount: Decimal,
    note: str | None = None,
) -> None:
    """Settle (pay down) credit balance."""
    actual = min(amount, account.balance)
    balance_before = account.balance
    account.balance -= actual
    db.add(CreditTransaction(
        id=uuid.uuid4(),
        credit_account_id=account.id,
        transaction_type="settlement",
        amount=actual,
        balance_before=balance_before,
        balance_after=account.balance,
        note=note,
    ))


async def adjust(
    db: AsyncSession,
    account: CreditAccount,
    delta: Decimal,
    note: str | None = None,
) -> None:
    """Manual balance adjustment (positive = increase balance owed)."""
    balance_before = account.balance
    account.balance += delta
    db.add(CreditTransaction(
        id=uuid.uuid4(),
        credit_account_id=account.id,
        transaction_type="adjustment",
        amount=delta,
        balance_before=balance_before,
        balance_after=account.balance,
        note=note,
    ))
