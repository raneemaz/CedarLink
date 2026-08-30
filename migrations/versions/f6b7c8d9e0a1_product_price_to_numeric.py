"""product.price Float -> Numeric(10, 2) (CL-07)

Money was Numeric(10, 2) everywhere (order totals, line unit prices,
payment amounts, store delivery fees) except Product.price, which was
Float. Checkout multiplied that float by a quantity and assigned the
result into a Numeric column. Align the column with the rest.

Revision ID: f6b7c8d9e0a1
Revises: e5a6b7c8d9f0
Create Date: 2026-08-30 00:00:01.000000

"""
from alembic import op
import sqlalchemy as sa


revision = "f6b7c8d9e0a1"
down_revision = "e5a6b7c8d9f0"
branch_labels = None
depends_on = None


def upgrade():
    with op.batch_alter_table("products", schema=None) as batch_op:
        batch_op.alter_column(
            "price",
            existing_type=sa.Float(),
            type_=sa.Numeric(10, 2),
            existing_nullable=False,
        )


def downgrade():
    with op.batch_alter_table("products", schema=None) as batch_op:
        batch_op.alter_column(
            "price",
            existing_type=sa.Numeric(10, 2),
            type_=sa.Float(),
            existing_nullable=False,
        )
