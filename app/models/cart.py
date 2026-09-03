from app.extensions import db


class Cart(db.Model):
    __tablename__ = "carts"
    id = db.Column(db.Integer, primary_key=True)

    user_id = db.Column(
        db.Integer,
        db.ForeignKey("users.id"),
        nullable=False,
        unique=True
    )
    # The coupon the customer has applied, if any. Held here rather than
    # in the client so it survives a reload and so DELETE /api/cart/coupon
    # has something to clear. Denormalised as the code, not an FK: the
    # coupon is re-validated on every pricing run anyway, and a code that
    # has since been deleted must fail validation, not break the cart.
    coupon_code = db.Column(db.String(40), nullable=True)

    items = db.relationship(
        "CartItem",
        back_populates="cart",
        cascade="all, delete-orphan"
    )

    user = db.relationship(
        "User",
        back_populates="cart"
    )
