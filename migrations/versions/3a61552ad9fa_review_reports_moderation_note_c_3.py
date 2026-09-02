"""review reports + moderation note (C.3)

New ``review_reports`` table — one row per (review, reporter) with a
reason, unique on that pair. ``reviews`` gains ``moderation_note`` for the
reason recorded on the last admin remove / restore.

See docs/decisions/0017-review-moderation.md.

Revision ID: 3a61552ad9fa
Revises: 0d106f16652f
Create Date: 2026-09-02 21:51:22.184458

"""
from alembic import op
import sqlalchemy as sa


revision = "3a61552ad9fa"
down_revision = "0d106f16652f"
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        "review_reports",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("review_id", sa.Integer(), nullable=False),
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.Column("reason", sa.String(length=500), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(["review_id"], ["reviews.id"]),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "review_id", "user_id", name="uq_review_reports_review_user"
        ),
    )
    with op.batch_alter_table("review_reports", schema=None) as batch_op:
        batch_op.create_index(
            "ix_review_reports_review_id", ["review_id"], unique=False
        )

    with op.batch_alter_table("reviews", schema=None) as batch_op:
        batch_op.add_column(
            sa.Column("moderation_note", sa.String(length=500), nullable=True)
        )


def downgrade():
    with op.batch_alter_table("reviews", schema=None) as batch_op:
        batch_op.drop_column("moderation_note")

    with op.batch_alter_table("review_reports", schema=None) as batch_op:
        batch_op.drop_index("ix_review_reports_review_id")

    op.drop_table("review_reports")
