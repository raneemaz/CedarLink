"""create notification preferences table

Revision ID: b8e4d1f96c23
Revises: a7f3c9e21d8b
Create Date: 2026-08-27 00:00:00.000000

"""

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = "b8e4d1f96c23"
down_revision = "a7f3c9e21d8b"
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        "notification_preferences",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.Column(
            "order_updates",
            sa.Boolean(),
            nullable=False,
            server_default=sa.true(),
        ),
        sa.Column(
            "promotions",
            sa.Boolean(),
            nullable=False,
            server_default=sa.false(),
        ),
        sa.Column(
            "email",
            sa.Boolean(),
            nullable=False,
            server_default=sa.true(),
        ),
        sa.Column(
            "in_app",
            sa.Boolean(),
            nullable=False,
            server_default=sa.true(),
        ),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("user_id"),
    )

    # Backfill one default row per existing user.
    op.execute(
        "INSERT INTO notification_preferences "
        "(user_id, order_updates, promotions, email, in_app, "
        "created_at, updated_at) "
        "SELECT id, 1, 0, 1, 1, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP "
        "FROM users"
    )


def downgrade():
    op.drop_table("notification_preferences")
