"""add language preference to users

Revision ID: d539dfdc41e8
Revises: f4c8a9d2b6e1
Create Date: 2026-08-25 14:46:17.141030

"""

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = "d539dfdc41e8"
down_revision = "f4c8a9d2b6e1"
branch_labels = None
depends_on = None


def upgrade():
    with op.batch_alter_table("users", schema=None) as batch_op:
        batch_op.add_column(
            sa.Column(
                "language",
                sa.Enum("en", "ar", "fr"),
                nullable=False,
                server_default="en",
            )
        )


def downgrade():
    with op.batch_alter_table("users", schema=None) as batch_op:
        batch_op.drop_column("language")
