"""store announcements (C.1)

New ``store_announcements`` table: a vendor notice shown on the store page
while ``is_active`` and the current time is inside ``[starts_at, ends_at)``
(``ends_at`` NULL = open-ended). Indexed on ``store_id`` and ``created_at``.

See docs/decisions/0014-store-announcements.md.

Revision ID: a1b2c3d4e5f6
Revises: d6f1a2b3c4e8
Create Date: 2026-09-02 00:00:00.000000

"""
from alembic import op
import sqlalchemy as sa


revision = "a1b2c3d4e5f6"
down_revision = "d6f1a2b3c4e8"
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        "store_announcements",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("store_id", sa.Integer(), nullable=False),
        sa.Column("title", sa.String(length=255), nullable=False),
        sa.Column("body", sa.Text(), nullable=False),
        sa.Column("starts_at", sa.DateTime(), nullable=False),
        sa.Column("ends_at", sa.DateTime(), nullable=True),
        sa.Column(
            "is_active",
            sa.Boolean(),
            server_default=sa.true(),
            nullable=False,
        ),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(["store_id"], ["stores.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "ix_store_announcements_store_id",
        "store_announcements",
        ["store_id"],
        unique=False,
    )
    op.create_index(
        "ix_store_announcements_created_at",
        "store_announcements",
        ["created_at"],
        unique=False,
    )


def downgrade():
    op.drop_index(
        "ix_store_announcements_created_at", table_name="store_announcements"
    )
    op.drop_index(
        "ix_store_announcements_store_id", table_name="store_announcements"
    )
    op.drop_table("store_announcements")
