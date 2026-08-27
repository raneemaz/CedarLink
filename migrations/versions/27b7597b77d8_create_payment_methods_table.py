"""create payment_methods table

Revision ID: 27b7597b77d8
Revises: 4d549b88efc4
Create Date: 2026-08-17 15:41:48.777599

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = "27b7597b77d8"
down_revision = "4d549b88efc4"
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        "payment_methods",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.Column("type", sa.String(length=30), nullable=False),
        sa.Column("label", sa.String(length=100), nullable=False),
        sa.Column("last4", sa.String(length=4), nullable=True),
        sa.Column("is_default", sa.Boolean(), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(
            ["user_id"],
            ["users.id"]
        ),
        sa.PrimaryKeyConstraint("id")
    )


def downgrade():
    op.drop_table("payment_methods")
