from app.extensions import db
from typing import TYPE_CHECKING

from app.models.category import SUPPORTED_LANGUAGES

if TYPE_CHECKING:
    from app.models.store import Store  # noqa: F401
    from app.models.category import Category  # noqa: F401


class Product(db.Model):
    __tablename__ = "products"
    __table_args__ = (
        # Last line of defence behind the conditional-UPDATE decrement
        # (CL-06). The column allowed negatives before.
        db.CheckConstraint("stock >= 0", name="ck_products_stock_non_negative"),
    )

    id = db.Column(db.Integer, primary_key=True)

    # name_en / description_en are the required canonical values; the _ar and
    # _fr columns are optional and fall back to English when blank. See
    # docs/decisions/0012-product-category-translation.md.
    name_en = db.Column(db.String(120), nullable=False)
    name_ar = db.Column(db.String(120), nullable=True)
    name_fr = db.Column(db.String(120), nullable=True)

    description_en = db.Column(db.Text, nullable=True)
    description_ar = db.Column(db.Text, nullable=True)
    description_fr = db.Column(db.Text, nullable=True)

    # Keep `product.name` / `product.description` working everywhere (queries,
    # factories, logs, error messages) as aliases for the English value.
    # Display surfaces use localized_name() / localized_description().
    name = db.synonym("name_en")
    description = db.synonym("description_en")

    # Money is Numeric(10, 2) everywhere — never Float (CL-07).
    price = db.Column(db.Numeric(10, 2), nullable=False)
    stock = db.Column(db.Integer, default=0)

    store_id = db.Column(db.Integer, db.ForeignKey("stores.id"),
                         nullable=False)
    category_id = db.Column(db.Integer, db.ForeignKey("categories.id"),
                            nullable=False)

    store = db.relationship(
        "Store",
        back_populates="products"
    )
    category = db.relationship(
        "Category",
        back_populates="products"
    )
    cart_items = db.relationship(
        "CartItem",
        back_populates="product"
    )

    # No delete-orphan cascade: order history must survive a product being
    # removed. Products are soft-deleted (deleted_at) instead — see
    # docs/decisions/0003-soft-delete-products.md.
    order_items = db.relationship(
        "OrderItem",
        back_populates="product"
    )

    images = db.relationship(
        "ProductImage",
        back_populates="product",
        cascade="all, delete-orphan"
    )
    created_at = db.Column(db.DateTime, default=db.func.now())
    updated_at = db.Column(db.DateTime, onupdate=db.func.now())
    deleted_at = db.Column(db.DateTime, nullable=True)

    def _localized(self, field, language):
        if language not in SUPPORTED_LANGUAGES:
            language = "en"
        value = getattr(self, f"{field}_{language}", None)
        if value and value.strip():
            return value
        return getattr(self, f"{field}_en")

    def localized_name(self, language):
        """The name in `language`, falling back to English (never blank)."""
        return self._localized("name", language)

    def localized_description(self, language):
        """The description in `language`, or the English one, or None."""
        return self._localized("description", language)

    def translations(self):
        """All translation columns, for the vendor edit form and serializers."""
        return {
            "name_en": self.name_en,
            "name_ar": self.name_ar,
            "name_fr": self.name_fr,
            "description_en": self.description_en,
            "description_ar": self.description_ar,
            "description_fr": self.description_fr,
        }

    def __repr__(self):
        return f"<Product {self.name_en}>"
