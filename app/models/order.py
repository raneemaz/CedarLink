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
