from app.extensions import db
from typing import TYPE_CHECKING

from app.models.category import SUPPORTED_LANGUAGES

if TYPE_CHECKING:
    from app.models.product import Product  # noqa: F401


class ProductOption(db.Model):
    """One option axis a vendor has defined on a product — "Colour", "Size".

    Additive: a product with no ``product_options`` rows is unaffected in
    every way — its own ``price`` and ``stock`` stay authoritative. See
    docs/decisions/0035-product-options-and-variants.md.
    """

    __tablename__ = "product_options"
    __table_args__ = (
        # Every read is "the options for this product" — the serializer and
        # the vendor form both start from a product_id.
        db.Index("ix_product_options_product_id", "product_id"),
    )

    id = db.Column(db.Integer, primary_key=True)

    product_id = db.Column(
        db.Integer,
        db.ForeignKey("products.id"),
        nullable=False,
    )

    # Same trilingual shape as every other name field (ADR 0012): English is
    # required, Arabic and French fall back to English when blank.
    name_en = db.Column(db.String(120), nullable=False)
    name_ar = db.Column(db.String(120), nullable=True)
    name_fr = db.Column(db.String(120), nullable=True)

    display_order = db.Column(
        db.Integer, nullable=False, default=0, server_default="0"
    )

    product = db.relationship("Product", back_populates="options")

    # Deleting an option deletes its values — the value set has no meaning
    # without the axis. Mirrors Product.images.
    values = db.relationship(
        "ProductOptionValue",
        back_populates="option",
        cascade="all, delete-orphan",
        order_by="ProductOptionValue.display_order",
    )

    def localized_name(self, language):
        """The name in `language`, falling back to English (never blank)."""
        if language not in SUPPORTED_LANGUAGES:
            language = "en"
        value = getattr(self, f"name_{language}", None)
        if value and value.strip():
            return value
        return self.name_en

    def __repr__(self):
        return f"<ProductOption {self.name_en}>"
