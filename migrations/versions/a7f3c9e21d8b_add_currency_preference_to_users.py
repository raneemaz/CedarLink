"""add currency preference to users

Revision ID: a7f3c9e21d8b
Revises: d539dfdc41e8
Create Date: 2026-08-27 00:00:00.000000

"""

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = "a7f3c9e21d8b"
down_revision = "d539dfdc41e8"
branch_labels = None
depends_on = None


def upgrade():
    with op.batch_alter_table("users", schema=None) as batch_op:
        batch_op.add_column(
            sa.Column(
                "currency",
                sa.Enum("USD", "LBP"),
                nullable=False,
                server_default="USD",
            )
        )


def downgrade():
    with op.batch_alter_table("users", schema=None) as batch_op:
        batch_op.drop_column("currency")
