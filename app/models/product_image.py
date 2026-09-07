from app.extensions import db
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from app.models.product import Product  # noqa: F401


class ProductImage(db.Model):
    __tablename__ = "product_images"
    __table_args__ = (
        # `WHERE product_id = ?` — one lookup per product in the listing
        # serializer, each a full scan without this (ADR 0032 F2).
        db.Index("ix_product_images_product_id", "product_id"),
    )

    id = db.Column(db.Integer, primary_key=True)
    image_url = db.Column(db.String(255), nullable=False)

    product_id = db.Column(
        db.Integer,
        db.ForeignKey("products.id"),
        nullable=False
    )

    product = db.relationship(
        "Product",
        back_populates="images"
    )

    def __repr__(self):
        return f"<ProductImage {self.id}>"
