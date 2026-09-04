"""orders.delivery_fee

Stores the delivery fee that was actually charged, instead of leaving it
to be recovered by subtraction. ``total_price = goods - discount +
delivery``, so ``total_price - goods`` was the fee only while nothing else
sat in that sum; coupons ended that.

Autogenerate produced a bare ``NOT NULL`` add, which fails against any
table that already has rows. Hand-edited into the three-step shape: add
nullable, backfill, tighten. The backfill runs the old derivation exactly
once, at the last moment it is still correct — every existing order
predates coupons or has a redemption row to add back.

Revision ID: 9e006e631fe8
Revises: 5b79a62a0984
Create Date: 2026-09-04 14:00:07.476839

"""
from decimal import Decimal

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision = '9e006e631fe8'
down_revision = '5b79a62a0984'
branch_labels = None
depends_on = None


def _backfill():
    """delivery_fee = total_price - goods + discount, per order.

    Done in Python rather than one UPDATE ... FROM so the arithmetic stays
    Decimal end to end (CLAUDE.md: money is never float) and the SQL stays
    portable — SQLite's two-argument MAX and Postgres's GREATEST are not
    the same function.
    """
    bind = op.get_bind()

    goods = dict(
        bind.execute(
            sa.text(
                "SELECT order_id, SUM(quantity * unit_price) "
                "FROM order_items GROUP BY order_id"
            )
        ).all()
    )
    discounts = dict(
        bind.execute(
            sa.text(
                "SELECT order_id, SUM(amount_applied) "
                "FROM coupon_redemptions GROUP BY order_id"
            )
        ).all()
    )

    rows = bind.execute(sa.text("SELECT id, total_price FROM orders")).all()

    for order_id, total_price in rows:
        fee = (
            Decimal(str(total_price))
            - Decimal(str(goods.get(order_id, 0) or 0))
            + Decimal(str(discounts.get(order_id, 0) or 0))
        )

        # A stored fee is never negative. Anything odd in historical data
        # lands on zero rather than on a number that reads as a refund.
        if fee < 0:
            fee = Decimal("0")

        bind.execute(
            sa.text("UPDATE orders SET delivery_fee = :fee WHERE id = :id"),
            {"fee": str(fee.quantize(Decimal("0.01"))), "id": order_id},
        )


def upgrade():
    with op.batch_alter_table('orders', schema=None) as batch_op:
        batch_op.add_column(
            sa.Column(
                'delivery_fee',
                sa.Numeric(precision=10, scale=2),
                nullable=True,
            )
        )

    _backfill()

    with op.batch_alter_table('orders', schema=None) as batch_op:
        batch_op.alter_column(
            'delivery_fee',
            existing_type=sa.Numeric(precision=10, scale=2),
            nullable=False,
        )


def downgrade():
    with op.batch_alter_table('orders', schema=None) as batch_op:
        batch_op.drop_column('delivery_fee')
