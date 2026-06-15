"""edge_step6_initial

Revision ID: 0001
Revises:
Create Date: 2026-01-01
"""
import sqlalchemy as sa

from alembic import op

revision = "0001"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "edge_categories",
        sa.Column("id", sa.UUID(as_uuid=True), primary_key=True),
        sa.Column("cloud_id", sa.UUID(as_uuid=True), nullable=False, unique=True),
        sa.Column("tenant_id", sa.UUID(as_uuid=True), nullable=False),
        sa.Column("name", sa.String(255), nullable=False),
        sa.Column("slug", sa.String(100), nullable=False),
        sa.Column("parent_id", sa.UUID(as_uuid=True), nullable=True),
        sa.Column("sort_order", sa.Integer, nullable=False, server_default="0"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("deleted_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("version", sa.Integer, nullable=False, server_default="1"),
    )
    op.create_table(
        "edge_products",
        sa.Column("id", sa.UUID(as_uuid=True), primary_key=True),
        sa.Column("cloud_id", sa.UUID(as_uuid=True), nullable=False, unique=True),
        sa.Column("tenant_id", sa.UUID(as_uuid=True), nullable=False),
        sa.Column("plu", sa.String(50), nullable=False),
        sa.Column("name", sa.String(255), nullable=False),
        sa.Column("vat_rate", sa.Numeric(5, 2), nullable=False, server_default="22"),
        sa.Column("unit", sa.String(10), nullable=False, server_default="piece"),
        sa.Column("is_weighable", sa.Boolean, nullable=False, server_default="false"),
        sa.Column("weight_grams", sa.Integer, nullable=True),
        sa.Column("weight_tolerance_pct", sa.Numeric(5, 2), nullable=True),
        sa.Column("age_restricted", sa.Boolean, nullable=False, server_default="false"),
        sa.Column("min_age", sa.Integer, nullable=True),
        sa.Column("allergens", sa.JSON, nullable=True),
        sa.Column("is_active", sa.Boolean, nullable=False, server_default="true"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("deleted_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("version", sa.Integer, nullable=False, server_default="1"),
    )
    op.create_table(
        "edge_barcodes",
        sa.Column("id", sa.UUID(as_uuid=True), primary_key=True),
        sa.Column("cloud_id", sa.UUID(as_uuid=True), nullable=False, unique=True),
        sa.Column("product_id", sa.UUID(as_uuid=True), sa.ForeignKey("edge_products.id"), nullable=False),
        sa.Column("code", sa.String(100), nullable=False, unique=True),
        sa.Column("barcode_type", sa.String(20), nullable=False, server_default="ean13"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("deleted_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("version", sa.Integer, nullable=False, server_default="1"),
    )
    op.create_table(
        "edge_prices",
        sa.Column("id", sa.UUID(as_uuid=True), primary_key=True),
        sa.Column("cloud_id", sa.UUID(as_uuid=True), nullable=False, unique=True),
        sa.Column("product_id", sa.UUID(as_uuid=True), sa.ForeignKey("edge_products.id"), nullable=False),
        sa.Column("price_type", sa.String(20), nullable=False, server_default="regular"),
        sa.Column("amount", sa.Numeric(10, 2), nullable=False),
        sa.Column("is_active", sa.Boolean, nullable=False, server_default="true"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("deleted_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("version", sa.Integer, nullable=False, server_default="1"),
    )
    op.create_table(
        "edge_stock_items",
        sa.Column("id", sa.UUID(as_uuid=True), primary_key=True),
        sa.Column("product_id", sa.UUID(as_uuid=True), nullable=False, unique=True),
        sa.Column("qty", sa.Numeric(14, 3), nullable=False, server_default="0"),
        sa.Column("reserved_qty", sa.Numeric(14, 3), nullable=False, server_default="0"),
        sa.Column("min_stock", sa.Numeric(14, 3), nullable=False, server_default="0"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("deleted_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("version", sa.Integer, nullable=False, server_default="1"),
    )
    op.create_table(
        "edge_stock_movements",
        sa.Column("id", sa.UUID(as_uuid=True), primary_key=True),
        sa.Column("product_id", sa.UUID(as_uuid=True), nullable=False),
        sa.Column("movement_type", sa.String(20), nullable=False),
        sa.Column("qty", sa.Numeric(14, 3), nullable=False),
        sa.Column("reference_id", sa.UUID(as_uuid=True), nullable=True),
        sa.Column("reference_type", sa.String(50), nullable=True),
        sa.Column("device_id", sa.UUID(as_uuid=True), nullable=True),
        sa.Column("occurred_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("synced_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("deleted_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("version", sa.Integer, nullable=False, server_default="1"),
    )
    op.create_index("ix_edge_movements_unsynced", "edge_stock_movements", ["synced_at"])
    op.create_table(
        "sync_queue",
        sa.Column("id", sa.UUID(as_uuid=True), primary_key=True),
        sa.Column("event_type", sa.String(50), nullable=False),
        sa.Column("payload", sa.JSON, nullable=False),
        sa.Column("status", sa.String(20), nullable=False, server_default="pending"),
        sa.Column("attempts", sa.Integer, nullable=False, server_default="0"),
        sa.Column("last_attempted_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("error", sa.String(500), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("deleted_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("version", sa.Integer, nullable=False, server_default="1"),
    )
    op.create_table(
        "sync_cursors",
        sa.Column("id", sa.UUID(as_uuid=True), primary_key=True),
        sa.Column("entity_type", sa.String(50), nullable=False, unique=True),
        sa.Column("pull_version", sa.Integer, nullable=False, server_default="0"),
        sa.Column("last_pulled_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("deleted_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("version", sa.Integer, nullable=False, server_default="1"),
    )


def downgrade() -> None:
    op.drop_table("sync_cursors")
    op.drop_table("sync_queue")
    op.drop_index("ix_edge_movements_unsynced", "edge_stock_movements")
    op.drop_table("edge_stock_movements")
    op.drop_table("edge_stock_items")
    op.drop_table("edge_prices")
    op.drop_table("edge_barcodes")
    op.drop_table("edge_products")
    op.drop_table("edge_categories")
