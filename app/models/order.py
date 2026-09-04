from datetime import datetime, timezone

from app.extensions import db


def _utc_now():
    """Timezone-aware UTC now — never ``datetime.utcnow`` (CLAUDE.md)."""
    return datetime.now(timezone.utc)


class Order(db.Model):
    __tablename__ = "orders"
    id = db.Column(db.Integer, primary_key=True)

    user_id = db.Column(
        db.Integer,
        db.ForeignKey("users.id"),
        nullable=False
    )

    store_id = db.Column(
        db.Integer,
        db.ForeignKey("stores.id"),
        nullable=False
    )

    status = db.Column(
        db.String(50),
        nullable=False,
        default="pending"
    )

    delivery_address = db.Column(
        db.String(255),
        nullable=False
    )

    delivery_city = db.Column(
        db.String(100),
        nullable=False
    )

    total_price = db.Column(
        db.Numeric(10, 2),
        nullable=False
    )

    # Stored, not derived. total_price = goods - discount + delivery, so a
    # client subtracting the goods from the total gets the fee only while
    # nothing else is in that sum — which stopped being true the day
    # coupons landed. Every term the server charges is a term the server
    # records.
    delivery_fee = db.Column(
        db.Numeric(10, 2),
        nullable=False,
        default=0
    )

    created_at = db.Column(
        db.DateTime,
        default=_utc_now,
        nullable=False
    )

    updated_at = db.Column(
        db.DateTime,
        default=_utc_now,
        onupdate=_utc_now,
        nullable=False
    )

    user = db.relationship(
        "User",
        back_populates="orders"
    )

    store = db.relationship(
        "Store",
        back_populates="orders"
    )

    # At most one, written in the same transaction as the order (ADR
    # 0021). viewonly: the redemption owns the link, and cancellation
    # deletes the row through coupon_service, not through this side.
    # selectin so serialising a list of orders stays one extra query.
    coupon_redemption = db.relationship(
        "CouponRedemption",
        uselist=False,
        viewonly=True,
        lazy="selectin",
    )

    items = db.relationship(
        "OrderItem",
        back_populates="order",
        cascade="all, delete-orphan"
    )

    payments = db.relationship(
        "Payment",
        back_populates="order",
        cascade="all, delete-orphan"
    )

    # No cascade: a review is verified-purchase evidence and must survive
    # anything short of the order itself being row-deleted (which does not
    # happen — orders are terminal, never deleted).
    reviews = db.relationship(
        "Review",
        back_populates="order",
    )
