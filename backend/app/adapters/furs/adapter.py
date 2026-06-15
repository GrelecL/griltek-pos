"""
FURS adapter — pluggable implementation.

MockFursAdapter  : dev/test, no network calls, fake EOR
RealFursAdapter  : production — SOAP calls to FURS endpoint (TODO: needs real cert)

Selection: FURS_ENV env var
  "mock"        → MockFursAdapter (default in dev)
  "test"        → MockFursAdapter (points at FURS beta, but still mocked here)
  "production"  → RealFursAdapter (requires FURS_CERT_PATH)
"""
import uuid
from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal
from typing import Protocol

from app.adapters.furs.zoi import compute_zoi_mock


@dataclass
class FursInvoiceRequest:
    tax_number: str
    issued_at: datetime
    invoice_number: str
    business_premise_id: str
    electronic_device_id: str
    invoice_amount: Decimal
    operator_tax_number: str | None = None  # cashier's tax number (optional per ZDavPR)


@dataclass
class FursInvoiceResponse:
    eor: str | None          # UUID from FURS; None if offline/failed
    zoi: str                 # always computed locally
    status: str              # "confirmed" | "pending" | "failed"
    raw_request: dict | None = None
    raw_response: dict | None = None
    error: str | None = None


class FursAdapter(Protocol):
    def confirm_invoice(self, req: FursInvoiceRequest) -> FursInvoiceResponse:
        ...

    def is_mock(self) -> bool:
        ...


class MockFursAdapter:
    """
    Mock FURS adapter for dev/test.
    Computes a deterministic fake ZOI; returns a random UUID as EOR.
    No network calls.
    """
    def confirm_invoice(self, req: FursInvoiceRequest) -> FursInvoiceResponse:
        zoi = compute_zoi_mock(
            req.tax_number, req.issued_at, req.invoice_number,
            req.business_premise_id, req.electronic_device_id, req.invoice_amount,
        )
        eor = str(uuid.uuid4())
        return FursInvoiceResponse(
            eor=eor,
            zoi=zoi,
            status="confirmed",
            raw_request={"mock": True, "invoice_number": req.invoice_number},
            raw_response={"eor": eor, "zoi": zoi},
        )

    def is_mock(self) -> bool:
        return True


class RealFursAdapter:
    """
    Real FURS adapter — SOAP calls to the FURS fiscalization service.

    # TODO: real impl
    # Requires:
    #   - FURS-issued certificate (.p12 or .pem) at FURS_CERT_PATH
    #   - cert password at FURS_CERT_PASSWORD
    #   - Endpoint: https://blagajna-test.fu.gov.si/ (test) or https://blagajna.fu.gov.si/ (prod)
    #   - zeep or requests with mutual TLS
    #   - ZOI from compute_zoi_real() with private key from certificate
    # See docs/FURS.md for full integration notes.
    """

    def confirm_invoice(self, req: FursInvoiceRequest) -> FursInvoiceResponse:
        # TODO: real impl — SOAP call with mTLS
        raise NotImplementedError(
            "Real FURS adapter not implemented. "
            "Set FURS_ENV=mock for development. "
            "See docs/FURS.md for production setup."
        )

    def is_mock(self) -> bool:
        return False


def get_furs_adapter() -> FursAdapter:
    """Return the configured FURS adapter based on FURS_ENV setting."""
    import os
    env = os.environ.get("FURS_ENV", "mock").lower()
    if env == "production":
        return RealFursAdapter()
    # "mock" or "test" → use mock adapter
    return MockFursAdapter()
