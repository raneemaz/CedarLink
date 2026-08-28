"""create shopping preferences table

Revision ID: d3f0a1b2c4e5
Revises: c4a9e7f2105d
Create Date: 2026-08-29 00:00:00.000000

"""

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = "d3f0a1b2c4e5"
down_revision = "c4a9e7f2105d"
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        "shopping_preferences",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.Column(
            "autofill_default_address",
            sa.Boolean(),
            nullable=False,
            server_default=sa.true(),
        ),
        sa.Column(
            "preferred_payment_method",
            sa.Enum("card", "cash_on_delivery"),
            nullable=False,
            server_default="cash_on_delivery",
        ),
        sa.Column("default_delivery_city", sa.String(length=100), nullable=True),
        sa.Column(
            "hide_out_of_stock",
            sa.Boolean(),
            nullable=False,
            server_default=sa.false(),
        ),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("user_id"),
    )

    # Backfill one default row per existing user.
    op.execute(
        "INSERT INTO shopping_preferences "
        "(user_id, autofill_default_address, preferred_payment_method, "
        "default_delivery_city, hide_out_of_stock, created_at, updated_at) "
        "SELECT id, 1, 'cash_on_delivery', NULL, 0, "
        "CURRENT_TIMESTAMP, CURRENT_TIMESTAMP FROM users"
    )


def downgrade():
    op.drop_table("shopping_preferences")
