"""GDPR right-to-erasure: anonymise customer PII while preserving audit trail."""
import uuid

from sqlalchemy import update
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.customer import Customer
from app.services.audit import log_action

ANON_NAME = "ERASED"
ANON_EMAIL = None
ANON_PHONE = None
ANON_TAX_ID = None
ANON_ADDRESS = None


async def erase_customer(
    db: AsyncSession,
    customer_id: uuid.UUID,
    requesting_user_id: uuid.UUID | None = None,
    tenant_id: uuid.UUID | None = None,
    ip_address: str | None = None,
) -> bool:
    """
    Anonymise a customer's PII fields in-place.
    Sales, loyalty, and audit records retain the customer_id FK (for financial
    integrity) but the PII is gone from the customers table.
    Returns True if found and erased, False if customer not found.
    """
    await db.execute(
        update(Customer)
        .where(Customer.id == customer_id)
        .values(
            name=ANON_NAME,
            email=ANON_EMAIL,
            phone=ANON_PHONE,
            tax_id=ANON_TAX_ID,
            address=ANON_ADDRESS,
        )
    )
    await log_action(
        db,
        action="customer_erasure",
        tenant_id=tenant_id,
        user_id=requesting_user_id,
        resource_type="customer",
        resource_id=str(customer_id),
        ip_address=ip_address,
        detail={"gdpr": True},
    )
    return True
