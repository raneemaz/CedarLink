"""indexes on orders, order_items, products, product_images, stores (ADR 0033)

Adds the secondary indexes the scale pass (ADR 0032 F1/F2/F6) found
missing. `orders`, `order_items` and `products` had no secondary index at
all, so every analytics query, product-listing filter and vendor lookup
was a full table scan. Index-only additions — no data change, no schema
reshape.

Revision ID: bac2fb1331ba
Revises: 352560c629d4
Create Date: 2026-09-07 16:17:20.358683
"""
from alembic import op


revision = 'bac2fb1331ba'
down_revision = '352560c629d4'
branch_labels = None
depends_on = None

_INDEXES = [
    # (name, table, columns)
    ("ix_orders_store_id_created_at", "orders", ["store_id", "created_at"]),
    ("ix_order_items_order_id", "order_items", ["order_id"]),
    ("ix_products_store_id", "products", ["store_id"]),
    ("ix_products_category_id", "products", ["category_id"]),
    ("ix_product_images_product_id", "product_images", ["product_id"]),
    ("ix_stores_owner_id", "stores", ["owner_id"]),
    ("ix_stores_name", "stores", ["name"]),
]


def upgrade():
    for name, table, columns in _INDEXES:
        op.create_index(name, table, columns, unique=False)


def downgrade():
    for name, table, _columns in reversed(_INDEXES):
        op.drop_index(name, table_name=table)
