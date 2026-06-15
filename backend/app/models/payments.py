"""Payment instrument models: gift cards, loyalty, credit transactions."""
import uuid
from datetime import datetime
from decimal import Decimal

from sqlalchemy import JSON, DateTime, ForeignKey, Numeric, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.db import Base
from app.models.base import TimestampMixin


class GiftCard(Base, TimestampMixin):
    __tablename__ = "gift_cards"
    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    tenant_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("tenants.id"))
    code: Mapped[str] = mapped_column(String(50), unique=True)
    initial_balance: Mapped[Decimal] = mapped_column(Numeric(12, 2))
    balance: Mapped[Decimal] = mapped_column(Numeric(12, 2))
    # status: active | redeemed | expired | cancelled
    status: Mapped[str] = mapped_column(String(20), default="active")
    valid_until: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    issued_to: Mapped[str | None] = mapped_column(String(255), nullable=True)
    transactions: Mapped[list["GiftCardTransaction"]] = relationship(back_populates="gift_card", cascade="all, delete-orphan")


class GiftCardTransaction(Base, TimestampMixin):
    __tablename__ = "gift_card_transactions"
    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    gift_card_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("gift_cards.id"))
    # type: issue | redeem | refund | topup | expire
    transaction_type: Mapped[str] = mapped_column(String(20))
    amount: Mapped[Decimal] = mapped_column(Numeric(12, 2))
    balance_before: Mapped[Decimal] = mapped_column(Numeric(12, 2))
    balance_after: Mapped[Decimal] = mapped_column(Numeric(12, 2))
    sale_id: Mapped[uuid.UUID | None] = mapped_column(nullable=True)
    note: Mapped[str | None] = mapped_column(String(300), nullable=True)
    gift_card: Mapped["GiftCard"] = relationship(back_populates="transactions")


class LoyaltyProgram(Base, TimestampMixin):
    """Tenant-level loyalty programme definition."""
    __tablename__ = "loyalty_programs"
    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    tenant_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("tenants.id"), unique=True)
    name: Mapped[str] = mapped_column(String(100))
    # points earned per euro spent (e.g. 1.0 = 1 point per €)
    earn_rate: Mapped[Decimal] = mapped_column(Numeric(8, 4), default=Decimal("1.0"))
    # euro value per point when redeeming (e.g. 0.01 = 1 point = €0.01)
    redeem_rate: Mapped[Decimal] = mapped_column(Numeric(8, 4), default=Decimal("0.01"))
    # minimum points required before redeeming
    min_redeem_points: Mapped[int] = mapped_column(default=100)
    is_active: Mapped[bool] = mapped_column(default=True)
    # tier thresholds: JSON list of {name, min_points, earn_multiplier}
    tiers: Mapped[list] = mapped_column(JSON, default=list)


class LoyaltyAccount(Base, TimestampMixin):
    __tablename__ = "loyalty_accounts"
    __table_args__ = (UniqueConstraint("program_id", "customer_id"),)
    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    program_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("loyalty_programs.id"))
    customer_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("customers.id"))
    points_balance: Mapped[int] = mapped_column(default=0)
    points_lifetime: Mapped[int] = mapped_column(default=0)
    tier: Mapped[str] = mapped_column(String(50), default="standard")
    is_active: Mapped[bool] = mapped_column(default=True)
    transactions: Mapped[list["LoyaltyTransaction"]] = relationship(back_populates="account", cascade="all, delete-orphan")


class LoyaltyTransaction(Base, TimestampMixin):
    __tablename__ = "loyalty_transactions"
    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    account_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("loyalty_accounts.id"))
    # type: earn | redeem | expire | adjust
    transaction_type: Mapped[str] = mapped_column(String(20))
    points: Mapped[int] = mapped_column()
    balance_before: Mapped[int] = mapped_column()
    balance_after: Mapped[int] = mapped_column()
    sale_id: Mapped[uuid.UUID | None] = mapped_column(nullable=True)
    note: Mapped[str | None] = mapped_column(String(300), nullable=True)
    account: Mapped["LoyaltyAccount"] = relationship(back_populates="transactions")


class CreditTransaction(Base, TimestampMixin):
    """Append-only ledger for credit account charges and settlements."""
    __tablename__ = "credit_transactions"
    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    credit_account_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("credit_accounts.id"))
    # type: charge | settlement | adjustment
    transaction_type: Mapped[str] = mapped_column(String(20))
    amount: Mapped[Decimal] = mapped_column(Numeric(12, 2))
    balance_before: Mapped[Decimal] = mapped_column(Numeric(12, 2))
    balance_after: Mapped[Decimal] = mapped_column(Numeric(12, 2))
    sale_id: Mapped[uuid.UUID | None] = mapped_column(nullable=True)
    note: Mapped[str | None] = mapped_column(String(300), nullable=True)
