"""ESL gateway adapter — mock for dev/test, stub for real hardware."""
from __future__ import annotations

from dataclasses import dataclass, field
from decimal import Decimal

from app.core.config import settings


@dataclass
class ESLLabelData:
    esl_id: str
    product_name: str
    plu: str
    price: Decimal
    original_price: Decimal | None = None  # set when a promo is active → shows strikethrough
    currency: str = "EUR"
    promo_label: str | None = None  # e.g. "10% OFF" displayed on the tag


@dataclass
class ESLPushResult:
    success: bool
    esl_id: str
    error: str = ""


class MockESLAdapter:
    """Records pushes in memory — used in tests and SUMUP_ENV=mock."""

    def __init__(self) -> None:
        self.pushed: list[ESLLabelData] = []

    async def push(self, label: ESLLabelData) -> ESLPushResult:
        self.pushed.append(label)
        return ESLPushResult(success=True, esl_id=label.esl_id)


class RealESLAdapter:
    """
    Stub for real ESL gateway integration.

    Implement by replacing the body of `push` with your gateway's HTTP call.
    Supported vendors: Hanshow Nebular, SoluM Newton, Pricer Plaza.
    Set ESL_GATEWAY_URL and ESL_GATEWAY_KEY in .env.
    """

    async def push(self, label: ESLLabelData) -> ESLPushResult:
        raise NotImplementedError(
            "Set ESL_ENV=real and implement RealESLAdapter.push() "
            "with your ESL gateway's HTTP API."
        )


_mock_instance = MockESLAdapter()


def get_esl_adapter() -> MockESLAdapter | RealESLAdapter:
    if getattr(settings, "esl_env", "mock") == "real":
        return RealESLAdapter()
    return _mock_instance
