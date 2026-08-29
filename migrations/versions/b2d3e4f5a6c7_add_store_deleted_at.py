"""add store deleted_at (admin soft delete)

See docs/decisions/0004-soft-delete-stores.md.

Revision ID: b2d3e4f5a6c7
Revises: a1c2e3f4b5d6
Create Date: 2026-08-29 00:00:00.000000

"""
from alembic import op
import sqlalchemy as sa


revision = "b2d3e4f5a6c7"
down_revision = "a1c2e3f4b5d6"
branch_labels = None
depends_on = None


def upgrade():
    with op.batch_alter_table("stores", schema=None) as batch_op:
        batch_op.add_column(
            sa.Column("deleted_at", sa.DateTime(), nullable=True)
        )


def downgrade():
    with op.batch_alter_table("stores", schema=None) as batch_op:
        batch_op.drop_column("deleted_at")
