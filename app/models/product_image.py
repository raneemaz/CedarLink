from app.extensions import db
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from app.models.product import Product


class ProductImage(db.Model):
    __tablename__ = "product_images"
    id = db.Column(db.Integer, primary_key=True)
    image_url = db.Column(db.String(255), nullable=False)

    product_id = db.Column(
        db.Integer,
        db.ForeignKey("products.id"),
        nullable=False
    )

    product = db.relationship("Product", backref="images")

    def __repr__(self):
        return f"<ProductImage {self.id}>"
