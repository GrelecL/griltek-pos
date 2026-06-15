"""Split payment processor: orchestrates cash, card, SumUp, gift, loyalty, credit."""
import uuid
from decimal import Decimal
from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from app.adapters.sumup.adapter import SumUpChargeRequest, get_sumup_adapter
from app.models.customer import CreditAccount
from app.models.payments import GiftCard, LoyaltyAccount, LoyaltyProgram
from app.models.pos import Payment
from app.services import credit as credit_svc
from app.services import gift_card as gc_svc
from app.services import loyalty as loyalty_svc


class PaymentLine:
    def __init__(self, method: str, amount: Decimal, reference: str = "", change_given: Decimal = Decimal("0")):
        self.method = method
        self.amount = amount
        self.reference = reference
        self.change_given = change_given


async def process_split_payments(
    db: AsyncSession,
    sale_id: uuid.UUID,
    total: Decimal,
    payment_requests: list[dict[str, Any]],
    customer_id: uuid.UUID | None = None,
    tenant_id: uuid.UUID | None = None,
) -> list[Payment]:
    """
    Process a list of payment requests against a sale total.

    Each request is a dict with keys:
      - method: cash | card | sumup | gift | loyalty | credit
      - amount: Decimal (or will be coerced)
      - reference: optional (gift card code, loyalty points count, etc.)

    Returns list of Payment objects (not yet committed).
    """
    payments: list[Payment] = []
    remaining = total

    for req in payment_requests:
        method = req["method"]
        amount = Decimal(str(req.get("amount", 0)))
        reference = str(req.get("reference", ""))

        if method == "cash":
            cash_given = Decimal(str(req.get("cash_given", amount)))
            change = max(Decimal("0"), cash_given - remaining)
            actual = min(amount, remaining)
            payments.append(Payment(
                id=uuid.uuid4(), sale_id=sale_id,
                method="cash", amount=actual,
                reference=None, change_given=change,
            ))
            remaining -= actual

        elif method == "card":
            actual = min(amount, remaining)
            payments.append(Payment(
                id=uuid.uuid4(), sale_id=sale_id,
                method="card", amount=actual,
                reference=reference or None,
            ))
            remaining -= actual

        elif method == "sumup":
            actual = min(amount, remaining)
            adapter = get_sumup_adapter()
            resp = await adapter.charge(SumUpChargeRequest(
                amount=str(actual), description=f"Sale {sale_id}"
            ))
            if not resp.approved:
                raise ValueError(f"SumUp payment declined: {resp.error}")
            payments.append(Payment(
                id=uuid.uuid4(), sale_id=sale_id,
                method="sumup", amount=actual,
                reference=resp.transaction_id,
            ))
            remaining -= actual

        elif method == "gift":
            card: GiftCard | None = await gc_svc.get_by_code(db, reference)
            if not card:
                raise ValueError(f"Gift card not found: {reference}")
            actual = await gc_svc.redeem(db, card, min(amount, remaining), sale_id=sale_id)
            payments.append(Payment(
                id=uuid.uuid4(), sale_id=sale_id,
                method="gift", amount=actual,
                reference=card.code,
            ))
            remaining -= actual

        elif method == "loyalty":
            if not customer_id or not tenant_id:
                raise ValueError("Customer and tenant required for loyalty payment")
            program: LoyaltyProgram | None = await loyalty_svc.get_program(db, tenant_id)
            if not program:
                raise ValueError("No active loyalty programme")
            account: LoyaltyAccount = await loyalty_svc.get_or_create_account(db, program.id, customer_id)
            points = int(req.get("points", 0))
            euro_value = await loyalty_svc.redeem_points(db, program, account, points, sale_id=sale_id)
            actual = min(euro_value, remaining)
            payments.append(Payment(
                id=uuid.uuid4(), sale_id=sale_id,
                method="loyalty", amount=actual,
                reference=f"{points}pts",
            ))
            remaining -= actual

        elif method == "credit":
            if not customer_id:
                raise ValueError("Customer required for credit payment")
            account_row: CreditAccount | None = await credit_svc.get_credit_account(db, customer_id)
            if not account_row:
                raise ValueError("Customer has no credit account")
            actual = min(amount, remaining)
            await credit_svc.charge(db, account_row, actual, sale_id=sale_id)
            payments.append(Payment(
                id=uuid.uuid4(), sale_id=sale_id,
                method="credit", amount=actual,
                reference=str(customer_id),
            ))
            remaining -= actual

        if remaining <= Decimal("0"):
            break

    if remaining > Decimal("0.005"):
        raise ValueError(f"Underpaid: {remaining} still outstanding after all payments")

    for p in payments:
        db.add(p)

    return payments
