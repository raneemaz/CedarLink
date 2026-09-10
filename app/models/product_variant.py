from app.extensions import db
from typing import TYPE_CHECKING

from app.models.category import SUPPORTED_LANGUAGES

if TYPE_CHECKING:
    from app.models.product import Product  # noqa: F401


class ProductVariant(db.Model):
    """One combination a vendor actually stocks — "Red, Medium".

    Not every value combination has to exist: a vendor who sells red in
    small and black in medium creates exactly those two rows.

    ``price`` when set is the price for this variant and the product's own
    ``price`` is ignored for it; when null the variant falls back to the
    product's price. ``stock`` is this variant's own stock — once a product
    has any variants, ``products.stock`` stops being read for purchasing
    (order_service), though it is not deleted. See
    docs/decisions/0035-product-options-and-variants.md.
    """

    __tablename__ = "product_variants"
    __table_args__ = (
        # Last line of defence behind the conditional-UPDATE decrement, the
        # same guard products.stock carries (CL-06 / ADR 0035).
        db.CheckConstraint(
            "stock >= 0", name="ck_product_variants_stock_non_negative"
        ),
        db.Index("ix_product_variants_product_id", "product_id"),
    )

    id = db.Column(db.Integer, primary_key=True)

    product_id = db.Column(
        db.Integer,
        db.ForeignKey("products.id"),
        nullable=False,
    )

    # The vendor's own reference, if they have one — not required.
    sku = db.Column(db.String(64), nullable=True)

    # Money is Numeric(10, 2) everywhere — never Float (CL-07). Nullable:
    # null means "use the product's price".
    price = db.Column(db.Numeric(10, 2), nullable=True)

    stock = db.Column(
        db.Integer, nullable=False, default=0, server_default="0"
    )

    # Lets a vendor retire one combination without deleting its order
    # history.
    is_active = db.Column(
        db.Boolean, nullable=False, default=True, server_default=db.true()
    )

    created_at = db.Column(db.DateTime, default=db.func.now())

    product = db.relationship("Product", back_populates="variants")

    # The variant's identity is the *set* of option values it combines.
    # Deleting the variant deletes the join rows, never the option values.
    values = db.relationship(
        "ProductVariantValue",
        back_populates="variant",
        cascade="all, delete-orphan",
    )

    def _ordered_values(self):
        """This variant's option values, in the axis then value order the
        vendor arranged — "Colour" before "Size", "Red" before "Blue"."""
        return sorted(
            (link.option_value for link in self.values),
            key=lambda ov: (
                ov.option.display_order,
                ov.display_order,
                ov.id,
            ),
        )

    def label(self, language):
        """"Red, Medium" in `language` — each value in its own trilingual
        text, comma-joined in display order. Not a translated sentence."""
        if language not in SUPPORTED_LANGUAGES:
            language = "en"
        return ", ".join(
            ov.localized_value(language) for ov in self._ordered_values()
        )

    def __repr__(self):
        return f"<ProductVariant {self.id} of product {self.product_id}>"
