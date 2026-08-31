from app.extensions import db

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from app.models.product import Product  # noqa: F401

# Three fixed interface languages. English is the required base; Arabic and
# French are optional and fall back to English when blank. See
# docs/decisions/0012-product-category-translation.md.
SUPPORTED_LANGUAGES = ("en", "ar", "fr")


class Category(db.Model):
    __tablename__ = "categories"
    id = db.Column(db.Integer, primary_key=True)

    # name_en is the required canonical value; name_ar / name_fr are optional.
    name_en = db.Column(db.String(100), nullable=False, unique=True)
    name_ar = db.Column(db.String(100), nullable=True)
    name_fr = db.Column(db.String(100), nullable=True)

    # `name` stays usable across the codebase (queries, factories, logs) as an
    # alias for the English value. Display code uses `localized_name()`.
    name = db.synonym("name_en")

    description = db.Column(db.Text, nullable=True)
    products = db.relationship(
        "Product",
        back_populates="category",
        lazy=True
    )

    def localized_name(self, language):
        """The name in `language`, falling back to English when blank."""
        if language not in SUPPORTED_LANGUAGES:
            language = "en"
        value = getattr(self, f"name_{language}", None)
        if value and value.strip():
            return value
        return self.name_en

    def to_dict(self):
        return {
            "id": self.id,
            "name_en": self.name_en,
            "name_ar": self.name_ar,
            "name_fr": self.name_fr,
            # English canonical, for any consumer not yet language-aware.
            "name": self.name_en,
            "description": self.description,
        }

    def __repr__(self):
        return f"<Category {self.name_en}>"
