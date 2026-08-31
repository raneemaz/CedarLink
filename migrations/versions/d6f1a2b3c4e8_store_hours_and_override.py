"""store working hours + manual open/closed override (C.1)

- new ``store_hours`` table: zero or more opening intervals per (store, day);
  no rows for a day means closed. Index on store_id.
- ``stores`` gains ``override_status`` / ``override_reason`` /
  ``override_until`` for a manual open/closed override that beats the
  schedule until it expires.

See docs/decisions/0013-store-hours-timezone.md.

Revision ID: d6f1a2b3c4e8
Revises: c5a1b2d3e4f7
Create Date: 2026-08-31 00:00:00.000000

"""
from alembic import op
import sqlalchemy as sa


revision = "d6f1a2b3c4e8"
down_revision = "c5a1b2d3e4f7"
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        "store_hours",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("store_id", sa.Integer(), nullable=False),
        sa.Column("day_of_week", sa.SmallInteger(), nullable=False),
        sa.Column("opens_at", sa.Time(), nullable=False),
        sa.Column("closes_at", sa.Time(), nullable=False),
        sa.ForeignKeyConstraint(["store_id"], ["stores.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "ix_store_hours_store_id", "store_hours", ["store_id"], unique=False
    )

    with op.batch_alter_table("stores", schema=None) as batch_op:
        batch_op.add_column(
            sa.Column("override_status", sa.String(length=10), nullable=True)
        )
        batch_op.add_column(
            sa.Column("override_reason", sa.String(length=255), nullable=True)
        )
        batch_op.add_column(
            sa.Column("override_until", sa.DateTime(), nullable=True)
        )


def downgrade():
    with op.batch_alter_table("stores", schema=None) as batch_op:
        batch_op.drop_column("override_until")
        batch_op.drop_column("override_reason")
        batch_op.drop_column("override_status")

    op.drop_index("ix_store_hours_store_id", table_name="store_hours")
    op.drop_table("store_hours")
