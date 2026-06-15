"""step5_fiscal

Revision ID: 0004
Revises: 0003
"""
import sqlalchemy as sa

from alembic import op

revision = "0004"
down_revision = "0003"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Add furs_tax_number to locations
    op.add_column("locations", sa.Column("furs_tax_number", sa.String(20), nullable=True))

    # Add furs_enabled to location_configs
    op.add_column("location_configs", sa.Column("furs_enabled", sa.Boolean, nullable=False, server_default="true"))

    # fiscal_counters
    op.create_table(
        "fiscal_counters",
        sa.Column("id", sa.UUID(as_uuid=True), primary_key=True),
        sa.Column("location_id", sa.UUID(as_uuid=True), sa.ForeignKey("locations.id"), nullable=False),
        sa.Column("business_premise_id", sa.String(20), nullable=False),
        sa.Column("electronic_device_id", sa.String(20), nullable=False),
        sa.Column("last_sequence", sa.Integer, nullable=False, server_default="0"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("deleted_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("version", sa.Integer, nullable=False, server_default="1"),
        sa.UniqueConstraint("location_id", "business_premise_id", "electronic_device_id",
                            name="uq_fiscal_counter"),
    )

    # fiscal_records
    op.create_table(
        "fiscal_records",
        sa.Column("id", sa.UUID(as_uuid=True), primary_key=True),
        sa.Column("sale_id", sa.UUID(as_uuid=True), sa.ForeignKey("sales.id"), nullable=False, unique=True),
        sa.Column("location_id", sa.UUID(as_uuid=True), sa.ForeignKey("locations.id"), nullable=False),
        sa.Column("invoice_number", sa.String(100), nullable=False),
        sa.Column("business_premise_id", sa.String(20), nullable=False),
        sa.Column("electronic_device_id", sa.String(20), nullable=False),
        sa.Column("invoice_amount", sa.Numeric(12, 2), nullable=False),
        sa.Column("tax_number", sa.String(20), nullable=True),
        sa.Column("issued_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("zoi", sa.String(32), nullable=True),
        sa.Column("eor", sa.String(36), nullable=True),
        sa.Column("status", sa.String(20), nullable=False, server_default="pending"),
        sa.Column("furs_request", sa.JSON, nullable=True),
        sa.Column("furs_response", sa.JSON, nullable=True),
        sa.Column("confirmed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("error_message", sa.String(500), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("deleted_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("version", sa.Integer, nullable=False, server_default="1"),
    )
    op.create_index("ix_fiscal_records_location_status", "fiscal_records", ["location_id", "status"])


def downgrade() -> None:
    op.drop_index("ix_fiscal_records_location_status", "fiscal_records")
    op.drop_table("fiscal_records")
    op.drop_table("fiscal_counters")
    op.drop_column("location_configs", "furs_enabled")
    op.drop_column("locations", "furs_tax_number")
