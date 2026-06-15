"""SumUp payment adapter.

MockSumUpAdapter: always approves — used in tests and dev.
RealSumUpAdapter: TODO — wire to SumUp Solo/Air SDK when hardware is available.
"""
import uuid
from dataclasses import dataclass

from app.core.config import settings


@dataclass
class SumUpChargeRequest:
    amount: str           # decimal string, e.g. "12.50"
    currency: str = "EUR"
    description: str = ""


@dataclass
class SumUpChargeResponse:
    approved: bool
    transaction_id: str
    amount: str
    error: str = ""


class MockSumUpAdapter:
    async def charge(self, req: SumUpChargeRequest) -> SumUpChargeResponse:
        return SumUpChargeResponse(
            approved=True,
            transaction_id=str(uuid.uuid4()),
            amount=req.amount,
        )


class RealSumUpAdapter:
    """
    TODO: implement using SumUp REST API or Solo SDK.
    Requires SUMUP_API_KEY in settings and a paired SumUp device.
    """
    async def charge(self, req: SumUpChargeRequest) -> SumUpChargeResponse:
        raise NotImplementedError("RealSumUpAdapter not yet implemented")


def get_sumup_adapter() -> MockSumUpAdapter | RealSumUpAdapter:
    if getattr(settings, "sumup_env", "mock") == "real":
        return RealSumUpAdapter()
    return MockSumUpAdapter()
