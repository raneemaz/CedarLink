"""index the remaining foreign keys

Thirteen foreign keys had no index. SQLite (like Postgres) indexes primary
keys and unique constraints automatically but never foreign keys, so each
of these was a full table scan on the child side of a join or filter.

The ones that are on a hot path:

  orders.user_id              every "my orders" page load
  cart_items.cart_id          every cart read, and the navbar badge
  coupon_redemptions.user_id  the per-user coupon limit, checked at every
                              checkout that carries a code
  addresses.user_id           the checkout address picker
  payment_methods.user_id     the checkout payment picker

The rest are colder but indexed for the same reason: a foreign key with no
index is a scan waiting for the table to grow. Index-only additions, no
data change, reversible.

Measured cost is negligible at current volumes -- these matter at the
scale ADR 0032 describes, not at seed size.

Revision ID: c7f1a9e2b40d
Revises: 5a89cc7c3038
Create Date: 2026-09-13 19:05:00.000000
"""
from alembic import op

# revision identifiers, used by Alembic.
revision = "c7f1a9e2b40d"
down_revision = "5a89cc7c3038"
branch_labels = None
depends_on = None


INDEXES = [
    ("ix_addresses_user_id", "addresses", ["user_id"]),
    ("ix_cart_items_cart_id", "cart_items", ["cart_id"]),
    ("ix_cart_items_product_id", "cart_items", ["product_id"]),
    ("ix_coupon_redemptions_order_id", "coupon_redemptions", ["order_id"]),
    ("ix_coupon_redemptions_user_id", "coupon_redemptions", ["user_id"]),
    ("ix_order_items_product_id", "order_items", ["product_id"]),
    ("ix_orders_user_id", "orders", ["user_id"]),
    ("ix_payment_methods_user_id", "payment_methods", ["user_id"]),
    ("ix_payments_payment_method_id", "payments", ["payment_method_id"]),
    (
        "ix_product_variant_values_option_value_id",
        "product_variant_values",
        ["option_value_id"],
    ),
    ("ix_review_reports_user_id", "review_reports", ["user_id"]),
    ("ix_reviews_order_id", "reviews", ["order_id"]),
    ("ix_shopping_interests_category_id", "shopping_interests",
     ["category_id"]),
]


def upgrade():
    for name, table, columns in INDEXES:
        op.create_index(name, table, columns, unique=False)


def downgrade():
    for name, table, _columns in reversed(INDEXES):
        op.drop_index(name, table_name=table)
