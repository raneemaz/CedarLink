"""add payment method number hash

Revision ID: b5fe5631dafe
Revises: 6320e427f109
Create Date: 2026-08-20 21:45:37.933359
"""

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = 'b5fe5631dafe'
down_revision = '6320e427f109'
branch_labels = None
depends_on = None


def upgrade():
    with op.batch_alter_table(
        'payment_methods',
        schema=None
    ) as batch_op:
        batch_op.add_column(
            sa.Column(
                'number_hash',
                sa.String(length=255),
                nullable=True
            )
        )


def downgrade():
    with op.batch_alter_table(
        'payment_methods',
        schema=None
    ) as batch_op:
        batch_op.drop_column('number_hash')
