"""add missing payment method provider fields

Revision ID: 6320e427f109
Revises: 62182cd5264a
Create Date: 2026-08-20 21:13:51.856144

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '6320e427f109'
down_revision = '62182cd5264a'
branch_labels = None
depends_on = None


def upgrade():
    with op.batch_alter_table('payment_methods', schema=None) as batch_op:
        batch_op.add_column(
            sa.Column('brand', sa.String(length=30), nullable=True)
        )
        batch_op.add_column(
            sa.Column('provider', sa.String(length=50), nullable=True)
        )
        batch_op.add_column(
            sa.Column(
                'provider_customer_id',
                sa.String(length=255),
                nullable=True
            )
        )
        batch_op.add_column(
            sa.Column(
                'provider_payment_method_id',
                sa.String(length=255),
                nullable=True
            )
        )

    # ### end Alembic commands ###


def downgrade():
    with op.batch_alter_table('payment_methods', schema=None) as batch_op:
        batch_op.drop_column('provider_payment_method_id')
        batch_op.drop_column('provider_customer_id')
        batch_op.drop_column('provider')
        batch_op.drop_column('brand')
    # ### end Alembic commands ###
