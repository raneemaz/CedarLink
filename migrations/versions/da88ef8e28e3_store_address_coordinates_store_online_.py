"""store + address coordinates, store online-only flag (C.2)

``stores`` and ``addresses`` each gain a nullable ``latitude`` /
``longitude`` (Numeric(9, 6)) map pin. ``stores`` also gets a composite
index on the pair (the distance search's bounding-box ``BETWEEN`` uses it
as a range scan) and ``is_online_only`` — an online-only store carries no
pin and never appears in a distance search.

See docs/decisions/0018-location-and-distance-search.md.

Revision ID: da88ef8e28e3
Revises: 3a61552ad9fa
Create Date: 2026-09-02 23:06:33.073423

"""
from alembic import op
import sqlalchemy as sa


revision = "da88ef8e28e3"
down_revision = "3a61552ad9fa"
branch_labels = None
depends_on = None


def upgrade():
    with op.batch_alter_table("addresses", schema=None) as batch_op:
        batch_op.add_column(
            sa.Column(
                "latitude", sa.Numeric(precision=9, scale=6), nullable=True
            )
        )
        batch_op.add_column(
            sa.Column(
                "longitude", sa.Numeric(precision=9, scale=6), nullable=True
            )
        )

    with op.batch_alter_table("stores", schema=None) as batch_op:
        batch_op.add_column(
            sa.Column(
                "latitude", sa.Numeric(precision=9, scale=6), nullable=True
            )
        )
        batch_op.add_column(
            sa.Column(
                "longitude", sa.Numeric(precision=9, scale=6), nullable=True
            )
        )
        batch_op.add_column(
            sa.Column(
                "is_online_only",
                sa.Boolean(),
                server_default=sa.text("0"),
                nullable=False,
            )
        )
        batch_op.create_index(
            "ix_stores_lat_lng", ["latitude", "longitude"], unique=False
        )


def downgrade():
    with op.batch_alter_table("stores", schema=None) as batch_op:
        batch_op.drop_index("ix_stores_lat_lng")
        batch_op.drop_column("is_online_only")
        batch_op.drop_column("longitude")
        batch_op.drop_column("latitude")

    with op.batch_alter_table("addresses", schema=None) as batch_op:
        batch_op.drop_column("longitude")
        batch_op.drop_column("latitude")
