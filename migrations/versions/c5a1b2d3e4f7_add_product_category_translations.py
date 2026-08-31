"""product & category name/description translations (C.5)

CLAUDE.md described Product / Category as carrying name_en / name_ar /
name_fr columns; they did not — each had a single `name`. This makes the
schema match that description.

  products:   name        -> name_en   (renamed, data preserved)
              description  -> description_en
              + name_ar, name_fr, description_ar, description_fr  (nullable)
  categories: name        -> name_en   (renamed, data preserved, UNIQUE kept)
              + name_ar, name_fr  (nullable)

The rename carries every existing row's value into the _en column, so no
backfill statement is needed and nothing is lost. Verified on a fresh
database in both directions.

See docs/decisions/0012-product-category-translation.md.

Revision ID: c5a1b2d3e4f7
Revises: a7c8d9e0f1b2
Create Date: 2026-08-31 00:00:00.000000

"""
from alembic import op
import sqlalchemy as sa


revision = "c5a1b2d3e4f7"
down_revision = "a7c8d9e0f1b2"
branch_labels = None
depends_on = None


def upgrade():
    with op.batch_alter_table("products", schema=None) as batch_op:
        batch_op.add_column(sa.Column("name_ar", sa.String(length=120),
                                      nullable=True))
        batch_op.add_column(sa.Column("name_fr", sa.String(length=120),
                                      nullable=True))
        batch_op.add_column(sa.Column("description_ar", sa.Text(),
                                      nullable=True))
        batch_op.add_column(sa.Column("description_fr", sa.Text(),
                                      nullable=True))
        batch_op.alter_column("name", new_column_name="name_en",
                              existing_type=sa.String(length=120),
                              existing_nullable=False)
        batch_op.alter_column("description", new_column_name="description_en",
                              existing_type=sa.Text(),
                              existing_nullable=True)

    with op.batch_alter_table("categories", schema=None) as batch_op:
        batch_op.add_column(sa.Column("name_ar", sa.String(length=100),
                                      nullable=True))
        batch_op.add_column(sa.Column("name_fr", sa.String(length=100),
                                      nullable=True))
        batch_op.alter_column("name", new_column_name="name_en",
                              existing_type=sa.String(length=100),
                              existing_nullable=False)


def downgrade():
    with op.batch_alter_table("categories", schema=None) as batch_op:
        batch_op.alter_column("name_en", new_column_name="name",
                              existing_type=sa.String(length=100),
                              existing_nullable=False)
        batch_op.drop_column("name_fr")
        batch_op.drop_column("name_ar")

    with op.batch_alter_table("products", schema=None) as batch_op:
        batch_op.alter_column("name_en", new_column_name="name",
                              existing_type=sa.String(length=120),
                              existing_nullable=False)
        batch_op.alter_column("description_en", new_column_name="description",
                              existing_type=sa.Text(),
                              existing_nullable=True)
        batch_op.drop_column("description_fr")
        batch_op.drop_column("description_ar")
        batch_op.drop_column("name_fr")
        batch_op.drop_column("name_ar")
