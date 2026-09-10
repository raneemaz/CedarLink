"""product options and variants (V-1 / ADR 0035)

Four new tables plus two additive, nullable column sets. Nothing existing
is renamed or dropped, and every new foreign key is nullable — a product
with no ``product_options`` rows is untouched and needs no data migration.

  product_options         one option axis per product ("Colour", "Size")
  product_option_values   one value per axis ("Red", "1L")
  product_variants        one stocked combination — own price (nullable,
                          falls back to the product) and own stock, with
                          the same ``stock >= 0`` CHECK products.stock has
  product_variant_values  (variant, option value) join, surrogate id +
                          unique pair, keyed like store_social_links

  cart_items.variant_id   nullable FK — null is the plain product line
  order_items.variant_id  nullable FK, plus variant_label_en/ar/fr, the
                          label denormalised at order time so a later
                          rename or retirement cannot rewrite history

Autogenerate produced this; reviewed by hand per the ADR 0016 warning —
the two FKs added to existing tables are named explicitly so the SQLite
batch rebuild can drop them by name on downgrade, and the CHECK constraint
on product_variants.stock was confirmed present.

Revision ID: 5a89cc7c3038
Revises: bac2fb1331ba
Create Date: 2026-09-10 17:29:46.805028
"""
from alembic import op
import sqlalchemy as sa


revision = "5a89cc7c3038"
down_revision = "bac2fb1331ba"
branch_labels = None
depends_on = None


_FK_CART_VARIANT = "fk_cart_items_variant_id_product_variants"
_FK_ORDER_VARIANT = "fk_order_items_variant_id_product_variants"


def upgrade():
    op.create_table(
        "product_options",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("product_id", sa.Integer(), nullable=False),
        sa.Column("name_en", sa.String(length=120), nullable=False),
        sa.Column("name_ar", sa.String(length=120), nullable=True),
        sa.Column("name_fr", sa.String(length=120), nullable=True),
        sa.Column(
            "display_order", sa.Integer(), server_default="0", nullable=False
        ),
        sa.ForeignKeyConstraint(["product_id"], ["products.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "ix_product_options_product_id", "product_options", ["product_id"]
    )

    op.create_table(
        "product_option_values",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("option_id", sa.Integer(), nullable=False),
        sa.Column("value_en", sa.String(length=120), nullable=False),
        sa.Column("value_ar", sa.String(length=120), nullable=True),
        sa.Column("value_fr", sa.String(length=120), nullable=True),
        sa.Column(
            "display_order", sa.Integer(), server_default="0", nullable=False
        ),
        sa.ForeignKeyConstraint(["option_id"], ["product_options.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "ix_product_option_values_option_id",
        "product_option_values",
        ["option_id"],
    )

    op.create_table(
        "product_variants",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("product_id", sa.Integer(), nullable=False),
        sa.Column("sku", sa.String(length=64), nullable=True),
        sa.Column("price", sa.Numeric(precision=10, scale=2), nullable=True),
        sa.Column("stock", sa.Integer(), server_default="0", nullable=False),
        sa.Column(
            "is_active",
            sa.Boolean(),
            server_default=sa.text("1"),
            nullable=False,
        ),
        sa.Column("created_at", sa.DateTime(), nullable=True),
        sa.CheckConstraint(
            "stock >= 0", name="ck_product_variants_stock_non_negative"
        ),
        sa.ForeignKeyConstraint(["product_id"], ["products.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "ix_product_variants_product_id", "product_variants", ["product_id"]
    )

    op.create_table(
        "product_variant_values",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("variant_id", sa.Integer(), nullable=False),
        sa.Column("option_value_id", sa.Integer(), nullable=False),
        sa.ForeignKeyConstraint(
            ["option_value_id"], ["product_option_values.id"]
        ),
        sa.ForeignKeyConstraint(["variant_id"], ["product_variants.id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "variant_id",
            "option_value_id",
            name="uq_product_variant_values_pair",
        ),
    )
    op.create_index(
        "ix_product_variant_values_variant_id",
        "product_variant_values",
        ["variant_id"],
    )

    with op.batch_alter_table("cart_items", schema=None) as batch_op:
        batch_op.add_column(
            sa.Column("variant_id", sa.Integer(), nullable=True)
        )
        batch_op.create_index(
            "ix_cart_items_variant_id", ["variant_id"], unique=False
        )
        batch_op.create_foreign_key(
            _FK_CART_VARIANT, "product_variants", ["variant_id"], ["id"]
        )

    with op.batch_alter_table("order_items", schema=None) as batch_op:
        batch_op.add_column(
            sa.Column("variant_id", sa.Integer(), nullable=True)
        )
        batch_op.add_column(
            sa.Column("variant_label_en", sa.String(length=255), nullable=True)
        )
        batch_op.add_column(
            sa.Column("variant_label_ar", sa.String(length=255), nullable=True)
        )
        batch_op.add_column(
            sa.Column("variant_label_fr", sa.String(length=255), nullable=True)
        )
        batch_op.create_index(
            "ix_order_items_variant_id", ["variant_id"], unique=False
        )
        batch_op.create_foreign_key(
            _FK_ORDER_VARIANT, "product_variants", ["variant_id"], ["id"]
        )


def downgrade():
    with op.batch_alter_table("order_items", schema=None) as batch_op:
        batch_op.drop_constraint(_FK_ORDER_VARIANT, type_="foreignkey")
        batch_op.drop_index("ix_order_items_variant_id")
        batch_op.drop_column("variant_label_fr")
        batch_op.drop_column("variant_label_ar")
        batch_op.drop_column("variant_label_en")
        batch_op.drop_column("variant_id")

    with op.batch_alter_table("cart_items", schema=None) as batch_op:
        batch_op.drop_constraint(_FK_CART_VARIANT, type_="foreignkey")
        batch_op.drop_index("ix_cart_items_variant_id")
        batch_op.drop_column("variant_id")

    op.drop_index(
        "ix_product_variant_values_variant_id",
        table_name="product_variant_values",
    )
    op.drop_table("product_variant_values")

    op.drop_index(
        "ix_product_variants_product_id", table_name="product_variants"
    )
    op.drop_table("product_variants")

    op.drop_index(
        "ix_product_option_values_option_id",
        table_name="product_option_values",
    )
    op.drop_table("product_option_values")

    op.drop_index(
        "ix_product_options_product_id", table_name="product_options"
    )
    op.drop_table("product_options")
