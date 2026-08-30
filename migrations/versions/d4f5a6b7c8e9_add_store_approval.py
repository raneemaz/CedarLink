"""add store approval gate

New stores start "pending" and are invisible to customers until an admin
approves them. Stores that predate this feature are grandfathered to
"approved" so nothing already live disappears.

See docs/decisions/0005-vendor-registration-and-store-approval.md.

Revision ID: d4f5a6b7c8e9
Revises: c3e4f5a6b7d8
Create Date: 2026-08-29 00:00:00.000000

"""
from alembic import op
import sqlalchemy as sa


revision = "d4f5a6b7c8e9"
down_revision = "c3e4f5a6b7d8"
branch_labels = None
depends_on = None


def upgrade():
    with op.batch_alter_table("stores", schema=None) as batch_op:
        batch_op.add_column(
            sa.Column(
                "approval_status",
                sa.String(length=20),
                nullable=False,
                server_default="pending",
            )
        )
        batch_op.add_column(
            sa.Column(
                "approval_note", sa.String(length=255), nullable=True
            )
        )

    # Grandfather every store that existed before the gate.
    op.execute("UPDATE stores SET approval_status = 'approved'")


def downgrade():
    with op.batch_alter_table("stores", schema=None) as batch_op:
        batch_op.drop_column("approval_note")
        batch_op.drop_column("approval_status")
