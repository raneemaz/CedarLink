from app.extensions import db


class OrderItem(db.Model):
    __tablename__ = "order_items"
    id = db.Column(db.Integer, primary_key=True)

    order_id = db.Column(
        db.Integer,
        db.ForeignKey("orders.id"),
        nullable=False
    )

    product_id = db.Column(
        db.Integer,
        db.ForeignKey("products.id"),
        nullable=False
    )

    quantity = db.Column(
        db.Integer,
        nullable=False
    )

    unit_price = db.Column(
        db.Numeric(10, 2),
        nullable=False
    )

    order = db.relationship(
        "Order",
        back_populates="items"
    )
    product = db.relationship(
        "Product",
        back_populates="order_items"
    )
    orders = db.relationship(
        "Order",
        back_populates="user",
        cascade="all, delete-orphan"
    )
    orders = db.relationship(
        "Order",
        back_populates="store",
        cascade="all, delete-orphan"
    )
    order_items = db.relationship(
        "OrderItem",
        back_populates="product"
    )
