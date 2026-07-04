from app.extensions import db


class CartItem(db.Model):
    __tablename__ = "cart_items"
    id = db.Column(db.Integer, primary_key=True)

    cart_id = db.Column(
        db.Integer,
        db.ForeignKey("carts.id"),
        nullable=False
    )

    product_id = db.Column(
        db.Integer,
        db.ForeignKey("products.id"),
        nullable=False
    )

    quantity = db.Column(
        db.Integer,
        nullable=False,
        default=1
    )

    cart = db.relationship(
        "Cart",
        back_populates="items"
    )

    product = db.relationship(
        "Product",
        back_populates="cart_items"
    )

    cart_items = db.relationship(
        "CartItem",
        back_populates="product"
    )
    