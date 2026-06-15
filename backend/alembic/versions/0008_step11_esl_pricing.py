"""Step 11: ESL devices and pricing rules."""
import sqlalchemy as sa
from alembic import op

revision = "0008"
down_revision = "0007"
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        "pricing_rules",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("tenant_id", sa.String(36), sa.ForeignKey("tenants.id"), nullable=False),
        sa.Column("name", sa.String(120), nullable=False),
        sa.Column("rule_type", sa.String(30), nullable=False),
        sa.Column("priority", sa.Integer, nullable=False, server_default="100"),
        sa.Column("conditions", sa.JSON, nullable=False, server_default="{}"),
        sa.Column("action", sa.JSON, nullable=False, server_default="{}"),
        sa.Column("is_active", sa.Boolean, nullable=False, server_default="1"),
        sa.Column("stackable", sa.Boolean, nullable=False, server_default="1"),
        sa.Column("valid_from", sa.DateTime(timezone=True), nullable=True),
        sa.Column("valid_until", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("deleted_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("version", sa.Integer, server_default="1"),
    )
    op.create_index("ix_pricing_rules_tenant_id", "pricing_rules", ["tenant_id"])
    op.create_index("ix_pricing_rules_priority", "pricing_rules", ["priority"])

    op.create_table(
        "esl_devices",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("location_id", sa.String(36), sa.ForeignKey("locations.id"), nullable=False),
        sa.Column("esl_id", sa.String(100), nullable=False),
        sa.Column("product_id", sa.String(36), sa.ForeignKey("products.id"), nullable=True),
        sa.Column("status", sa.String(20), nullable=False, server_default="pending"),
        sa.Column("last_synced_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("last_price", sa.Numeric(10, 2), nullable=True),
        sa.Column("last_error", sa.String(255), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("deleted_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("version", sa.Integer, server_default="1"),
        sa.UniqueConstraint("location_id", "esl_id", name="uq_esl_location_id"),
    )
    op.create_index("ix_esl_devices_location_id", "esl_devices", ["location_id"])
    op.create_index("ix_esl_devices_product_id", "esl_devices", ["product_id"])


def downgrade():
    op.drop_index("ix_esl_devices_product_id", "esl_devices")
    op.drop_index("ix_esl_devices_location_id", "esl_devices")
    op.drop_table("esl_devices")
    op.drop_index("ix_pricing_rules_priority", "pricing_rules")
    op.drop_index("ix_pricing_rules_tenant_id", "pricing_rules")
    op.drop_table("pricing_rules")
