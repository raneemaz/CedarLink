from datetime import datetime, timezone

from app.extensions import db


def _utc_now():
    """Timezone-aware UTC now — never ``datetime.utcnow`` (CLAUDE.md)."""
    return datetime.now(timezone.utc)


def _utc_isoformat(value):
    if value is None:
        return None
    if value.tzinfo is None:
        value = value.replace(tzinfo=timezone.utc)
    return value.isoformat()


class CouponRedemption(db.Model):
    """The audit trail: what a coupon actually took off, for whom, on which
    order.

    ``amount_applied`` is recorded rather than recomputed. A coupon's value
    can be edited or the coupon deactivated after the fact, so the only
    trustworthy answer to "what discount did this order get?" is the number
    written when the order was placed.

    Written inside the same transaction as the order, and deleted (with
    ``used_count`` decremented) when a pending order is cancelled — the same
    symmetry as restoring stock.

    No cascade onto orders in either direction.
    """

    __tablename__ = "coupon_redemptions"
    __table_args__ = (
        # The per-user limit counts rows here for one (coupon, user) pair;
        # this is the index that read serves.
        db.Index(
            "ix_coupon_redemptions_coupon_id_user_id", "coupon_id", "user_id"
        ),
    )

    id = db.Column(db.Integer, primary_key=True)

    coupon_id = db.Column(
        db.Integer, db.ForeignKey("coupons.id"), nullable=False
    )
    user_id = db.Column(
        db.Integer, db.ForeignKey("users.id"), nullable=False
    )
    order_id = db.Column(
        db.Integer, db.ForeignKey("orders.id"), nullable=False
    )

    amount_applied = db.Column(db.Numeric(10, 2), nullable=False)

    created_at = db.Column(db.DateTime, nullable=False, default=_utc_now)

    coupon = db.relationship("Coupon", back_populates="redemptions")
    user = db.relationship("User")
    order = db.relationship("Order")

    def to_dict(self):
        return {
            "id": self.id,
            "coupon_id": self.coupon_id,
            "user_id": self.user_id,
            "order_id": self.order_id,
            "amount_applied": float(self.amount_applied),
            "created_at": _utc_isoformat(self.created_at),
        }
