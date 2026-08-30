"""products.stock non-negative check (CL-06)

The checkout decrement is now a conditional UPDATE
(``... WHERE stock >= :qty``) so stock cannot go negative through the
application. This CHECK constraint is the last line of defence at the
database — the column allowed negatives before.

Revision ID: e5a6b7c8d9f0
Revises: d4f5a6b7c8e9
Create Date: 2026-08-30 00:00:00.000000

"""
from alembic import op


revision = "e5a6b7c8d9f0"
down_revision = "d4f5a6b7c8e9"
branch_labels = None
depends_on = None


def upgrade():
    # Guard against pre-existing bad data before the constraint is enforced.
    op.execute("UPDATE products SET stock = 0 WHERE stock < 0")

    with op.batch_alter_table("products", schema=None) as batch_op:
        batch_op.create_check_constraint(
            "ck_products_stock_non_negative", "stock >= 0"
        )


def downgrade():
    with op.batch_alter_table("products", schema=None) as batch_op:
        batch_op.drop_constraint(
            "ck_products_stock_non_negative", type_="check"
        )
