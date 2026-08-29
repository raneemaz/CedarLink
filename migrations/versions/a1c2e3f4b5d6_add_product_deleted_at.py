"""add product deleted_at (soft delete)

See docs/decisions/0003-soft-delete-products.md.

Revision ID: a1c2e3f4b5d6
Revises: f1a2b3c4d5e6
Create Date: 2026-08-29 00:00:00.000000

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = "a1c2e3f4b5d6"
down_revision = "f1a2b3c4d5e6"
branch_labels = None
depends_on = None


def upgrade():
    with op.batch_alter_table("products", schema=None) as batch_op:
        batch_op.add_column(
            sa.Column("deleted_at", sa.DateTime(), nullable=True)
        )


def downgrade():
    with op.batch_alter_table("products", schema=None) as batch_op:
        batch_op.drop_column("deleted_at")
