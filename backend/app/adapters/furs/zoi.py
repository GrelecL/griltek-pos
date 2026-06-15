"""
ZOI (Zaščitna Oznaka Izdajatelja) calculation per ZDavPR specification.

Algorithm:
1. Build concatenated string from invoice fields
2. Sign with merchant's RSA private key (SHA-256)
3. MD5 of the raw signature bytes = ZOI (32 hex chars)

In mock mode: generate a deterministic MD5 from invoice fields (no real key needed).
In real mode: requires FURS-issued certificate with private key.
"""
import hashlib
from datetime import datetime
from decimal import Decimal


def _zoi_input_string(
    tax_number: str,
    issued_at: datetime,
    invoice_number: str,
    business_premise_id: str,
    electronic_device_id: str,
    invoice_amount: Decimal,
) -> str:
    """Build the concatenated input string for ZOI signing (per ZDavPR §7)."""
    amount_str = f"{invoice_amount:.2f}"
    dt_str = issued_at.strftime("%Y-%m-%dT%H:%M:%S")
    return (
        f"{tax_number}{dt_str}{invoice_number}"
        f"{business_premise_id}{electronic_device_id}{amount_str}"
    )


def compute_zoi_mock(
    tax_number: str,
    issued_at: datetime,
    invoice_number: str,
    business_premise_id: str,
    electronic_device_id: str,
    invoice_amount: Decimal,
) -> str:
    """
    Mock ZOI: MD5 of the input string (no real RSA key).
    Used in dev/test. NOT valid for FURS submission.
    """
    data = _zoi_input_string(
        tax_number, issued_at, invoice_number,
        business_premise_id, electronic_device_id, invoice_amount,
    )
    return hashlib.md5(data.encode("utf-8")).hexdigest()


def compute_zoi_real(
    tax_number: str,
    issued_at: datetime,
    invoice_number: str,
    business_premise_id: str,
    electronic_device_id: str,
    invoice_amount: Decimal,
    private_key_pem: bytes,
) -> str:
    """
    Real ZOI per ZDavPR: RSA-SHA256 sign → MD5 of signature bytes.
    Requires merchant's FURS-issued private key (PEM).
    """
    # TODO: real impl — obtain FURS certificate
    from cryptography.hazmat.primitives import hashes, serialization
    from cryptography.hazmat.primitives.asymmetric import padding

    data = _zoi_input_string(
        tax_number, issued_at, invoice_number,
        business_premise_id, electronic_device_id, invoice_amount,
    ).encode("utf-8")

    private_key = serialization.load_pem_private_key(private_key_pem, password=None)
    signature = private_key.sign(data, padding.PKCS1v15(), hashes.SHA256())
    return hashlib.md5(signature).hexdigest()
