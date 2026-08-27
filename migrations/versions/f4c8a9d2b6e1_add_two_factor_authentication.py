"""add two factor authentication

Revision ID: f4c8a9d2b6e1
Revises: e1b9c4d2f7a6
Create Date: 2026-08-22 14:00:00.000000
"""

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = "f4c8a9d2b6e1"
down_revision = "e1b9c4d2f7a6"
branch_labels = None
depends_on = None


def upgrade():
    with op.batch_alter_table("users", schema=None) as batch_op:
        batch_op.add_column(
            sa.Column(
                "two_factor_enabled",
                sa.Boolean(),
                nullable=False,
                server_default=sa.false()
            )
        )
        batch_op.add_column(
            sa.Column(
                "two_factor_method",
                sa.String(length=20),
                nullable=True
            )
        )
        batch_op.add_column(
            sa.Column(
                "two_factor_totp_secret",
                sa.Text(),
                nullable=True
            )
        )

    op.create_table(
        "two_factor_challenges",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.Column("token_hash", sa.String(length=64), nullable=False),
        sa.Column("purpose", sa.String(length=30), nullable=False),
        sa.Column("method", sa.String(length=20), nullable=False),
        sa.Column("code_hash", sa.String(length=255), nullable=True),
        sa.Column("totp_secret_encrypted", sa.Text(), nullable=True),
        sa.Column("expires_at", sa.DateTime(), nullable=False),
        sa.Column("attempt_count", sa.Integer(), nullable=False),
        sa.Column("send_count", sa.Integer(), nullable=False),
        sa.Column("last_sent_at", sa.DateTime(), nullable=True),
        sa.Column("consumed_at", sa.DateTime(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("token_hash")
    )
    op.create_index(
        "ix_two_factor_challenges_user_id",
        "two_factor_challenges",
        ["user_id"]
    )
    op.create_index(
        "ix_two_factor_challenges_purpose",
        "two_factor_challenges",
        ["purpose"]
    )
    op.create_index(
        "ix_two_factor_challenges_expires_at",
        "two_factor_challenges",
        ["expires_at"]
    )

    op.create_table(
        "two_factor_recovery_codes",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.Column("code_hash", sa.String(length=255), nullable=False),
        sa.Column("used", sa.Boolean(), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("used_at", sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"]),
        sa.PrimaryKeyConstraint("id")
    )
    op.create_index(
        "ix_two_factor_recovery_codes_user_id",
        "two_factor_recovery_codes",
        ["user_id"]
    )


def downgrade():
    op.drop_index(
        "ix_two_factor_recovery_codes_user_id",
        table_name="two_factor_recovery_codes"
    )
    op.drop_table("two_factor_recovery_codes")

    op.drop_index(
        "ix_two_factor_challenges_expires_at",
        table_name="two_factor_challenges"
    )
    op.drop_index(
        "ix_two_factor_challenges_purpose",
        table_name="two_factor_challenges"
    )
    op.drop_index(
        "ix_two_factor_challenges_user_id",
        table_name="two_factor_challenges"
    )
    op.drop_table("two_factor_challenges")

    with op.batch_alter_table("users", schema=None) as batch_op:
        batch_op.drop_column("two_factor_totp_secret")
        batch_op.drop_column("two_factor_method")
        batch_op.drop_column("two_factor_enabled")
