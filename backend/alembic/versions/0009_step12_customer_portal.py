"""Step 12: customer portal accounts and coupons."""
import sqlalchemy as sa
from alembic import op

revision = "0009"
down_revision = "0008"
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        "customer_portal_accounts",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("customer_id", sa.String(36), sa.ForeignKey("customers.id"),
                  nullable=False, unique=True),
        sa.Column("pin_hash", sa.String(64), nullable=False),
        sa.Column("is_active", sa.Boolean, nullable=False, server_default="1"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("deleted_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("version", sa.Integer, server_default="1"),
    )

    op.create_table(
        "coupons",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("tenant_id", sa.String(36), sa.ForeignKey("tenants.id"), nullable=False),
        sa.Column("code", sa.String(60), nullable=False, unique=True),
        sa.Column("name", sa.String(120), nullable=False),
        sa.Column("description", sa.String(500), nullable=True),
        sa.Column("discount_type", sa.String(30), nullable=False),
        sa.Column("discount_value", sa.Numeric(10, 2), nullable=False),
        sa.Column("min_purchase", sa.Numeric(10, 2), nullable=True),
        sa.Column("valid_from", sa.DateTime(timezone=True), nullable=True),
        sa.Column("valid_until", sa.DateTime(timezone=True), nullable=True),
        sa.Column("max_uses", sa.Integer, nullable=True),
        sa.Column("per_customer_limit", sa.Integer, nullable=False, server_default="1"),
        sa.Column("used_count", sa.Integer, nullable=False, server_default="0"),
        sa.Column("is_active", sa.Boolean, nullable=False, server_default="1"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("deleted_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("version", sa.Integer, server_default="1"),
    )
    op.create_index("ix_coupons_tenant_id", "coupons", ["tenant_id"])

    op.create_table(
        "coupon_redemptions",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("coupon_id", sa.String(36), sa.ForeignKey("coupons.id"), nullable=False),
        sa.Column("customer_id", sa.String(36), sa.ForeignKey("customers.id"), nullable=False),
        sa.Column("sale_id", sa.String(36), sa.ForeignKey("sales.id"), nullable=True),
        sa.Column("redeemed_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("deleted_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("version", sa.Integer, server_default="1"),
    )
    op.create_index("ix_coupon_redemptions_customer_id", "coupon_redemptions", ["customer_id"])
    op.create_index("ix_coupon_redemptions_coupon_id", "coupon_redemptions", ["coupon_id"])


def downgrade():
    op.drop_index("ix_coupon_redemptions_coupon_id", "coupon_redemptions")
    op.drop_index("ix_coupon_redemptions_customer_id", "coupon_redemptions")
    op.drop_table("coupon_redemptions")
    op.drop_index("ix_coupons_tenant_id", "coupons")
    op.drop_table("coupons")
    op.drop_table("customer_portal_accounts")
