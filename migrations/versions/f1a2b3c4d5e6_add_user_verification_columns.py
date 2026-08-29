"""add user verification columns

The ``is_verified`` and ``verification_method`` columns on ``users`` were
added to development databases out of band and never captured as a
migration, so ``flask db upgrade`` could not build a working schema from a
fresh clone. This revision records them.

It is written to be safe on databases that already have the columns (it
checks first and does nothing), so existing environments upgrade cleanly.

Revision ID: f1a2b3c4d5e6
Revises: e4b1c2d3f5a6
Create Date: 2026-08-29 00:00:00.000000

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = 'f1a2b3c4d5e6'
down_revision = 'e4b1c2d3f5a6'
branch_labels = None
depends_on = None


def _existing_user_columns():
    bind = op.get_bind()
    return {column["name"] for column in sa.inspect(bind).get_columns("users")}


def upgrade():
    existing = _existing_user_columns()

    columns_to_add = []

    if "is_verified" not in existing:
        columns_to_add.append(
            sa.Column(
                "is_verified",
                sa.Boolean(),
                nullable=False,
                server_default=sa.false(),
            )
        )

    if "verification_method" not in existing:
        columns_to_add.append(
            sa.Column(
                "verification_method",
                sa.String(length=20),
                nullable=True,
            )
        )

    if not columns_to_add:
        return

    with op.batch_alter_table("users", schema=None) as batch_op:
        for column in columns_to_add:
            batch_op.add_column(column)


def downgrade():
    existing = _existing_user_columns()

    with op.batch_alter_table("users", schema=None) as batch_op:
        if "verification_method" in existing:
            batch_op.drop_column("verification_method")
        if "is_verified" in existing:
            batch_op.drop_column("is_verified")
