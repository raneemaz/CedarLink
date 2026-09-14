from app.extensions import db
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from app.models.product_variant import ProductVariant  # noqa: F401
    from app.models.product_option_value import ProductOptionValue  # noqa: F401


class ProductVariantValue(db.Model):
    """One (variant, option value) pair.

    Surrogate ``id`` plus a unique constraint on the pair, the way
    ``store_social_links`` keys a per-store-per-platform row rather than a
    composite primary key.
    """

    __tablename__ = "product_variant_values"
    __table_args__ = (
        db.Index("ix_product_variant_values_option_value_id", "option_value_id"),
        db.UniqueConstraint(
            "variant_id",
            "option_value_id",
            name="uq_product_variant_values_pair",
        ),
        db.Index("ix_product_variant_values_variant_id", "variant_id"),
    )

    id = db.Column(db.Integer, primary_key=True)

    variant_id = db.Column(
        db.Integer,
        db.ForeignKey("product_variants.id"),
        nullable=False,
    )

    option_value_id = db.Column(
        db.Integer,
        db.ForeignKey("product_option_values.id"),
        nullable=False,
    )

    variant = db.relationship("ProductVariant", back_populates="values")

    # No back_populates: the option value does not need to know which
    # variants use it, and a soft link keeps the cascade one-directional.
    option_value = db.relationship("ProductOptionValue")

    def __repr__(self):
        return (
            f"<ProductVariantValue variant={self.variant_id} "
            f"value={self.option_value_id}>"
        )
