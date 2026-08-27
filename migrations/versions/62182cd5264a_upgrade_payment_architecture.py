"""upgrade payment architecture

Revision ID: 62182cd5264a
Revises: 27b7597b77d8
Create Date: 2026-08-17 19:18:40.550330

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '62182cd5264a'
down_revision = '27b7597b77d8'
branch_labels = None
depends_on = None


def upgrade():
    # payment_methods columns already exist in the database.
    # Only add the missing payment columns.

    with op.batch_alter_table('payments', schema=None) as batch_op:
        batch_op.add_column(
            sa.Column(
                'provider',
                sa.String(length=50),
                nullable=True
            )
        )
        batch_op.add_column(
            sa.Column(
                'provider_payment_id',
                sa.String(length=255),
                nullable=True
            )
        )
        batch_op.add_column(
            sa.Column(
                'payment_method_id',
                sa.Integer(),
                nullable=True
            )
        )

        batch_op.create_foreign_key(
            'fk_payments_payment_method_id',
            'payment_methods',
            ['payment_method_id'],
            ['id']
        )


def downgrade():
    with op.batch_alter_table('payments', schema=None) as batch_op:
        batch_op.drop_constraint(
            'fk_payments_payment_method_id',
            type_='foreignkey'
        )
        batch_op.drop_column('payment_method_id')
        batch_op.drop_column('provider_payment_id')
        batch_op.drop_column('provider')
