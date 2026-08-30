"""token revocation: denylist table + users.tokens_revoked_at (CL-09)

Revision ID: a7c8d9e0f1b2
Revises: f6b7c8d9e0a1
Create Date: 2026-08-30 00:00:02.000000

"""
from alembic import op
import sqlalchemy as sa


revision = "a7c8d9e0f1b2"
down_revision = "f6b7c8d9e0a1"
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        "token_denylist",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("jti", sa.String(length=36), nullable=False),
        sa.Column("token_type", sa.String(length=10), nullable=False),
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("expires_at", sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    with op.batch_alter_table("token_denylist", schema=None) as batch_op:
        batch_op.create_index(
            batch_op.f("ix_token_denylist_jti"), ["jti"], unique=True
        )
        batch_op.create_index(
            batch_op.f("ix_token_denylist_user_id"), ["user_id"], unique=False
        )

    with op.batch_alter_table("users", schema=None) as batch_op:
        batch_op.add_column(
            sa.Column("tokens_revoked_at", sa.DateTime(), nullable=True)
        )


def downgrade():
    with op.batch_alter_table("users", schema=None) as batch_op:
        batch_op.drop_column("tokens_revoked_at")

    with op.batch_alter_table("token_denylist", schema=None) as batch_op:
        batch_op.drop_index(batch_op.f("ix_token_denylist_user_id"))
        batch_op.drop_index(batch_op.f("ix_token_denylist_jti"))

    op.drop_table("token_denylist")
