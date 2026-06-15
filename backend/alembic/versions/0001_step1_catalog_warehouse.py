"""step1_catalog_warehouse

Revision ID: 0001
Revises:
Create Date: 2026-06-14 00:00:00.000000

"""

import sqlalchemy as sa

from alembic import op

revision = "0001"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    # 1. tenants
    op.create_table(
        "tenants",
        sa.Column("id", sa.UUID(as_uuid=True), primary_key=True),
        sa.Column("name", sa.String(255), nullable=False),
        sa.Column("slug", sa.String(100), nullable=False, unique=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("deleted_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("version", sa.Integer, default=1, nullable=False),
    )

    # 2. plans
    op.create_table(
        "plans",
        sa.Column("id", sa.UUID(as_uuid=True), primary_key=True),
        sa.Column("name", sa.String(100), nullable=False),
        sa.Column("max_locations", sa.Integer, default=1, nullable=False),
        sa.Column("max_devices", sa.Integer, default=5, nullable=False),
        sa.Column("price_monthly", sa.Numeric(10, 2), default=0, nullable=False),
        sa.Column("features", sa.JSON, nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("deleted_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("version", sa.Integer, default=1, nullable=False),
    )

    # 3. subscriptions (refs tenants, plans)
    op.create_table(
        "subscriptions",
        sa.Column("id", sa.UUID(as_uuid=True), primary_key=True),
        sa.Column("tenant_id", sa.UUID(as_uuid=True), sa.ForeignKey("tenants.id"), nullable=False),
        sa.Column("plan_id", sa.UUID(as_uuid=True), sa.ForeignKey("plans.id"), nullable=False),
        sa.Column("status", sa.String(20), default="trial", nullable=False),
        sa.Column("period_start", sa.DateTime(timezone=True), nullable=False),
        sa.Column("period_end", sa.DateTime(timezone=True), nullable=False),
        sa.Column("billing_reference", sa.String(255), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("deleted_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("version", sa.Integer, default=1, nullable=False),
    )
    op.create_index("ix_subscriptions_tenant_id", "subscriptions", ["tenant_id"])

    # 4. locations (refs tenants)
    op.create_table(
        "locations",
        sa.Column("id", sa.UUID(as_uuid=True), primary_key=True),
        sa.Column("tenant_id", sa.UUID(as_uuid=True), sa.ForeignKey("tenants.id"), nullable=False),
        sa.Column("name", sa.String(255), nullable=False),
        sa.Column("address", sa.String(500), nullable=True),
        sa.Column("business_type", sa.String(20), default="retail", nullable=False),
        sa.Column("furs_business_premise_id", sa.String(100), nullable=True),
        sa.Column("timezone", sa.String(50), default="Europe/Ljubljana", nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("deleted_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("version", sa.Integer, default=1, nullable=False),
    )
    op.create_index("ix_locations_tenant_id", "locations", ["tenant_id"])

    # 5. location_configs (refs locations)
    op.create_table(
        "location_configs",
        sa.Column("id", sa.UUID(as_uuid=True), primary_key=True),
        sa.Column("location_id", sa.UUID(as_uuid=True), sa.ForeignKey("locations.id"), nullable=False, unique=True),
        sa.Column("self_checkout", sa.Boolean, default=False, nullable=False),
        sa.Column("price_check", sa.Boolean, default=False, nullable=False),
        sa.Column("order_kiosk", sa.Boolean, default=False, nullable=False),
        sa.Column("kds", sa.Boolean, default=False, nullable=False),
        sa.Column("tables", sa.Boolean, default=False, nullable=False),
        sa.Column("open_tabs", sa.Boolean, default=False, nullable=False),
        sa.Column("courses", sa.Boolean, default=False, nullable=False),
        sa.Column("tips", sa.Boolean, default=False, nullable=False),
        sa.Column("security_scale", sa.Boolean, default=False, nullable=False),
        sa.Column("vat_eat_in", sa.Numeric(5, 2), default=9.5, nullable=False),
        sa.Column("vat_take_away", sa.Numeric(5, 2), default=9.5, nullable=False),
        sa.Column("currency", sa.String(3), default="EUR", nullable=False),
        sa.Column("cash_rounding", sa.Boolean, default=False, nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("deleted_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("version", sa.Integer, default=1, nullable=False),
    )

    # 6. categories (refs tenants, self)
    op.create_table(
        "categories",
        sa.Column("id", sa.UUID(as_uuid=True), primary_key=True),
        sa.Column("tenant_id", sa.UUID(as_uuid=True), sa.ForeignKey("tenants.id"), nullable=False),
        sa.Column("parent_id", sa.UUID(as_uuid=True), sa.ForeignKey("categories.id"), nullable=True),
        sa.Column("name", sa.String(255), nullable=False),
        sa.Column("slug", sa.String(100), nullable=False),
        sa.Column("sort_order", sa.Integer, default=0, nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("deleted_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("version", sa.Integer, default=1, nullable=False),
        sa.UniqueConstraint("tenant_id", "slug", name="uq_category_tenant_slug"),
    )
    op.create_index("ix_categories_tenant_id", "categories", ["tenant_id"])

    # 7. products (refs tenants, categories)
    op.create_table(
        "products",
        sa.Column("id", sa.UUID(as_uuid=True), primary_key=True),
        sa.Column("tenant_id", sa.UUID(as_uuid=True), sa.ForeignKey("tenants.id"), nullable=False),
        sa.Column("category_id", sa.UUID(as_uuid=True), sa.ForeignKey("categories.id"), nullable=True),
        sa.Column("plu", sa.String(50), nullable=False),
        sa.Column("name", sa.String(255), nullable=False),
        sa.Column("description", sa.String(2000), nullable=True),
        sa.Column("vat_rate", sa.Numeric(5, 2), default=22, nullable=False),
        sa.Column("unit", sa.String(10), default="piece", nullable=False),
        sa.Column("is_weighable", sa.Boolean, default=False, nullable=False),
        sa.Column("weight_grams", sa.Integer, nullable=True),
        sa.Column("weight_tolerance_pct", sa.Numeric(5, 2), nullable=True),
        sa.Column("age_restricted", sa.Boolean, default=False, nullable=False),
        sa.Column("min_age", sa.Integer, nullable=True),
        sa.Column("allergens", sa.JSON, nullable=True),
        sa.Column("modifiers", sa.JSON, nullable=True),
        sa.Column("image_url", sa.String(1000), nullable=True),
        sa.Column("is_active", sa.Boolean, default=True, nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("deleted_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("version", sa.Integer, default=1, nullable=False),
        sa.UniqueConstraint("tenant_id", "plu", name="uq_product_tenant_plu"),
    )
    op.create_index("ix_products_tenant_id", "products", ["tenant_id"])

    # 8. barcodes (refs products)
    op.create_table(
        "barcodes",
        sa.Column("id", sa.UUID(as_uuid=True), primary_key=True),
        sa.Column("product_id", sa.UUID(as_uuid=True), sa.ForeignKey("products.id"), nullable=False),
        sa.Column("code", sa.String(100), nullable=False, unique=True),
        sa.Column("barcode_type", sa.String(20), default="ean13", nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("deleted_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("version", sa.Integer, default=1, nullable=False),
    )
    op.create_index("ix_barcodes_product_id", "barcodes", ["product_id"])

    # 9. prices (refs products, locations)
    op.create_table(
        "prices",
        sa.Column("id", sa.UUID(as_uuid=True), primary_key=True),
        sa.Column("product_id", sa.UUID(as_uuid=True), sa.ForeignKey("products.id"), nullable=False),
        sa.Column("location_id", sa.UUID(as_uuid=True), sa.ForeignKey("locations.id"), nullable=True),
        sa.Column("price_type", sa.String(20), default="regular", nullable=False),
        sa.Column("amount", sa.Numeric(10, 2), nullable=False),
        sa.Column("valid_from", sa.DateTime(timezone=True), nullable=True),
        sa.Column("valid_until", sa.DateTime(timezone=True), nullable=True),
        sa.Column("min_qty", sa.Integer, default=1, nullable=False),
        sa.Column("is_active", sa.Boolean, default=True, nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("deleted_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("version", sa.Integer, default=1, nullable=False),
    )
    op.create_index("ix_prices_product_id", "prices", ["product_id"])

    # 10. warehouses (refs tenants, locations)
    op.create_table(
        "warehouses",
        sa.Column("id", sa.UUID(as_uuid=True), primary_key=True),
        sa.Column("tenant_id", sa.UUID(as_uuid=True), sa.ForeignKey("tenants.id"), nullable=False),
        sa.Column("location_id", sa.UUID(as_uuid=True), sa.ForeignKey("locations.id"), nullable=True),
        sa.Column("name", sa.String(255), nullable=False),
        sa.Column("is_default", sa.Boolean, default=False, nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("deleted_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("version", sa.Integer, default=1, nullable=False),
    )
    op.create_index("ix_warehouses_tenant_id", "warehouses", ["tenant_id"])

    # 11. stock_items (refs products, warehouses)
    op.create_table(
        "stock_items",
        sa.Column("id", sa.UUID(as_uuid=True), primary_key=True),
        sa.Column("product_id", sa.UUID(as_uuid=True), sa.ForeignKey("products.id"), nullable=False),
        sa.Column("warehouse_id", sa.UUID(as_uuid=True), sa.ForeignKey("warehouses.id"), nullable=False),
        sa.Column("qty", sa.Numeric(14, 3), default=0, nullable=False),
        sa.Column("reserved_qty", sa.Numeric(14, 3), default=0, nullable=False),
        sa.Column("min_stock", sa.Numeric(14, 3), default=0, nullable=False),
        sa.Column("max_stock", sa.Numeric(14, 3), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("deleted_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("version", sa.Integer, default=1, nullable=False),
        sa.UniqueConstraint("product_id", "warehouse_id", name="uq_stock_product_warehouse"),
    )

    # 12. stock_movements (refs products, warehouses, locations)
    op.create_table(
        "stock_movements",
        sa.Column("id", sa.UUID(as_uuid=True), primary_key=True),
        sa.Column("product_id", sa.UUID(as_uuid=True), sa.ForeignKey("products.id"), nullable=False),
        sa.Column("warehouse_id", sa.UUID(as_uuid=True), sa.ForeignKey("warehouses.id"), nullable=False),
        sa.Column("movement_type", sa.String(20), nullable=False),
        sa.Column("qty", sa.Numeric(14, 3), nullable=False),
        sa.Column("reference_id", sa.UUID(as_uuid=True), nullable=True),
        sa.Column("reference_type", sa.String(50), nullable=True),
        sa.Column("device_id", sa.UUID(as_uuid=True), nullable=True),
        sa.Column("location_id", sa.UUID(as_uuid=True), sa.ForeignKey("locations.id"), nullable=True),
        sa.Column("note", sa.String(500), nullable=True),
        sa.Column("occurred_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("deleted_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("version", sa.Integer, default=1, nullable=False),
    )
    op.create_index("ix_stock_movements_product_id", "stock_movements", ["product_id"])
    op.create_index("ix_stock_movements_warehouse_id", "stock_movements", ["warehouse_id"])
    op.create_index("ix_stock_movements_occurred_at", "stock_movements", ["occurred_at"])


def downgrade() -> None:
    op.drop_table("stock_movements")
    op.drop_table("stock_items")
    op.drop_table("warehouses")
    op.drop_table("prices")
    op.drop_table("barcodes")
    op.drop_table("products")
    op.drop_table("categories")
    op.drop_table("location_configs")
    op.drop_table("locations")
    op.drop_table("subscriptions")
    op.drop_table("plans")
    op.drop_table("tenants")
