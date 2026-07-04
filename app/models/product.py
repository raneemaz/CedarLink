from app.extensions import db
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from app.models.store import Store
    from app.models.category import Category


class Product(db.Model):
    __tablename__ = "products"

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(120), nullable=False)
    description = db.Column(db.Text, nullable=True)
    price = db.Column(db.Float, nullable=False)
    stock = db.Column(db.Integer, default=0)

    store_id = db.Column(db.Integer, db.ForeignKey("stores.id"),
                         nullable=False)
    category_id = db.Column(db.Integer, db.ForeignKey("categories.id"),
                            nullable=False)

    store = db.relationship("Store", backref="products")
    category = db.relationship("Category", backref="products")
    cart_items = db.relationship(
        "CartItem",
        back_populates="product"
    )
    images = db.relationship(
        "ProductImage",
        back_populates="product",
        cascade="all, delete-orphan"
    )
    created_at = db.Column(db.DateTime, default=db.func.now())
    updated_at = db.Column(db.DateTime, onupdate=db.func.now())

    def __repr__(self):
        return f"<Product {self.name}>"
    
