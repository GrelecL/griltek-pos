import uuid

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.customer import CreditAccount, Customer
from app.schemas.customer import CreditAccountCreate, CustomerCreate, CustomerUpdate


async def create_customer(db: AsyncSession, data: CustomerCreate) -> Customer:
    obj = Customer(**data.model_dump())
    db.add(obj)
    await db.commit()
    await db.refresh(obj)
    return obj


async def get_customer(db: AsyncSession, customer_id: uuid.UUID) -> Customer | None:
    result = await db.execute(
        select(Customer).where(
            Customer.id == customer_id, Customer.deleted_at.is_(None)
        )
    )
    return result.scalar_one_or_none()


async def list_customers(
    db: AsyncSession, tenant_id: uuid.UUID, search: str | None = None
) -> list[Customer]:
    q = select(Customer).where(
        Customer.tenant_id == tenant_id, Customer.deleted_at.is_(None)
    )
    if search:
        q = q.where(Customer.name.ilike(f"%{search}%"))
    result = await db.execute(q.order_by(Customer.name))
    return list(result.scalars().all())


async def update_customer(
    db: AsyncSession, customer_id: uuid.UUID, data: CustomerUpdate
) -> Customer | None:
    obj = await get_customer(db, customer_id)
    if not obj:
        return None
    for k, v in data.model_dump(exclude_none=True).items():
        setattr(obj, k, v)
    obj.version += 1
    await db.commit()
    await db.refresh(obj)
    return obj


async def create_credit_account(
    db: AsyncSession, data: CreditAccountCreate
) -> CreditAccount:
    obj = CreditAccount(**data.model_dump())
    db.add(obj)
    await db.commit()
    await db.refresh(obj)
    return obj


async def get_credit_account(
    db: AsyncSession, customer_id: uuid.UUID
) -> CreditAccount | None:
    result = await db.execute(
        select(CreditAccount).where(CreditAccount.customer_id == customer_id)
    )
    return result.scalar_one_or_none()
