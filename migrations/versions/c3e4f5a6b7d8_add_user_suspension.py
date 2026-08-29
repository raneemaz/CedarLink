"""add user suspension (admin-controlled)

suspended_at / suspension_reason are separate from is_active so a suspended
user cannot lift their own suspension through /auth/reactivate.

Revision ID: c3e4f5a6b7d8
Revises: b2d3e4f5a6c7
Create Date: 2026-08-29 00:00:01.000000

"""
from alembic import op
import sqlalchemy as sa


revision = "c3e4f5a6b7d8"
down_revision = "b2d3e4f5a6c7"
branch_labels = None
depends_on = None


def upgrade():
    with op.batch_alter_table("users", schema=None) as batch_op:
        batch_op.add_column(
            sa.Column("suspended_at", sa.DateTime(), nullable=True)
        )
        batch_op.add_column(
            sa.Column(
                "suspension_reason", sa.String(length=255), nullable=True
            )
        )


def downgrade():
    with op.batch_alter_table("users", schema=None) as batch_op:
        batch_op.drop_column("suspension_reason")
        batch_op.drop_column("suspended_at")
