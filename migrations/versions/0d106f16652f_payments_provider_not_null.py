"""payments.provider NOT NULL

The model has always declared ``provider`` as ``nullable=False`` and the only
code that inserts a ``Payment`` (``payment_routes.create_payment``) always
sets it to a non-null constant. Migration ``62182cd5264a`` added the column
as ``nullable=True`` and the two never got reconciled — one of the two
drifts closed by docs/decisions/0016-model-migration-drift-guard.md.

SQLite cannot ``ALTER COLUMN``, so this goes through Alembic batch mode
(table rebuild). The defensive ``UPDATE`` backfills any legacy NULL row —
``cedarlink`` is the provider every current method maps to — so the rebuild
cannot fail on existing data even though a from-empty database has none.

Revision ID: 0d106f16652f
Revises: a128e4a1eead
Create Date: 2026-09-02 18:43:52.862778

"""
from alembic import op
import sqlalchemy as sa


revision = '0d106f16652f'
down_revision = 'a128e4a1eead'
branch_labels = None
depends_on = None


def upgrade():
    op.execute(
        "UPDATE payments SET provider = 'cedarlink' WHERE provider IS NULL"
    )
    with op.batch_alter_table('payments', schema=None) as batch_op:
        batch_op.alter_column(
            'provider',
            existing_type=sa.VARCHAR(length=50),
            nullable=False,
        )


def downgrade():
    with op.batch_alter_table('payments', schema=None) as batch_op:
        batch_op.alter_column(
            'provider',
            existing_type=sa.VARCHAR(length=50),
            nullable=True,
        )
