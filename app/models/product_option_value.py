from app.extensions import db
from typing import TYPE_CHECKING

from app.models.category import SUPPORTED_LANGUAGES

if TYPE_CHECKING:
    from app.models.product_option import ProductOption  # noqa: F401


class ProductOptionValue(db.Model):
    """One value within an option axis — "Red" / "Black" under "Colour"."""

    __tablename__ = "product_option_values"
    __table_args__ = (
        db.Index("ix_product_option_values_option_id", "option_id"),
    )

    id = db.Column(db.Integer, primary_key=True)

    option_id = db.Column(
        db.Integer,
        db.ForeignKey("product_options.id"),
        nullable=False,
    )

    # Trilingual, English required (ADR 0012).
    value_en = db.Column(db.String(120), nullable=False)
    value_ar = db.Column(db.String(120), nullable=True)
    value_fr = db.Column(db.String(120), nullable=True)

    display_order = db.Column(
        db.Integer, nullable=False, default=0, server_default="0"
    )

    option = db.relationship("ProductOption", back_populates="values")

    def localized_value(self, language):
        """The value in `language`, falling back to English (never blank)."""
        if language not in SUPPORTED_LANGUAGES:
            language = "en"
        value = getattr(self, f"value_{language}", None)
        if value and value.strip():
            return value
        return self.value_en

    def __repr__(self):
        return f"<ProductOptionValue {self.value_en}>"
