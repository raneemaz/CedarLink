from datetime import datetime, timezone

from app.extensions import db


def _utc_now():
    """Timezone-aware UTC now — never ``datetime.utcnow`` (CLAUDE.md)."""
    return datetime.now(timezone.utc)


def _utc_isoformat(value):
    """A stored datetime as an explicit-UTC ISO 8601 string.

    SQLite drops the offset on read, so a value written aware comes back
    naive-representing-UTC; annotate it so ``new Date(...)`` is unambiguous.
    """
    if value is None:
        return None
    if value.tzinfo is None:
        value = value.replace(tzinfo=timezone.utc)
    return value.isoformat()


PERCENTAGE = "percentage"
FIXED = "fixed"
DISCOUNT_TYPES = (PERCENTAGE, FIXED)


class Coupon(db.Model):
    """A discount code, either platform-wide or scoped to one store.

    ``store_id`` NULL means platform-wide; set means that store only. A
    vendor may only ever create the scoped kind — enforced in the route,
    asserted in the tests.

    ``usage_limit`` / ``per_user_limit`` NULL mean unlimited. ``used_count``
    is claimed with a conditional UPDATE at checkout, never read-then-
    written, so two concurrent checkouts cannot both take the last use. See
    docs/decisions/0021-coupons-and-discounts.md.

    No cascade reaches orders. A coupon must never be deletable in a way
    that rewrites order history — the redemption row is the audit trail of
    what was actually taken off, and it outlives nothing but itself.
    """

    __tablename__ = "coupons"
    __table_args__ = (
        db.CheckConstraint(
            "discount_type IN ('percentage', 'fixed')",
            name="ck_coupons_discount_type",
        ),
        # A percentage is 1-100; a fixed amount is any positive money value.
        db.CheckConstraint(
            "(discount_type = 'percentage' AND value >= 1 AND value <= 100) "
            "OR (discount_type = 'fixed' AND value > 0)",
            name="ck_coupons_value_range",
        ),
        db.CheckConstraint(
            "min_order_total IS NULL OR min_order_total >= 0",
            name="ck_coupons_min_order_total_non_negative",
        ),
        db.CheckConstraint(
            "usage_limit IS NULL OR usage_limit >= 1",
            name="ck_coupons_usage_limit_positive",
        ),
        db.CheckConstraint(
            "per_user_limit IS NULL OR per_user_limit >= 1",
            name="ck_coupons_per_user_limit_positive",
        ),
        db.CheckConstraint(
            "used_count >= 0",
            name="ck_coupons_used_count_non_negative",
        ),
        db.Index("ix_coupons_store_id", "store_id"),
    )

    id = db.Column(db.Integer, primary_key=True)

    # Stored uppercase and trimmed by coupon_service.normalize_code, so the
    # unique index is the case-insensitive match — no LOWER() on the column
    # and no collation dependency.
    code = db.Column(db.String(40), nullable=False, unique=True)

    discount_type = db.Column(db.String(20), nullable=False)

    # Money and percentages are both Decimal — never float (CLAUDE.md).
    value = db.Column(db.Numeric(10, 2), nullable=False)

    min_order_total = db.Column(db.Numeric(10, 2), nullable=True)

    starts_at = db.Column(db.DateTime, nullable=True)
    ends_at = db.Column(db.DateTime, nullable=True)

    # NULL means unlimited, for both.
    usage_limit = db.Column(db.Integer, nullable=True)
    per_user_limit = db.Column(db.Integer, nullable=True)

    used_count = db.Column(db.Integer, nullable=False, default=0)

    store_id = db.Column(
        db.Integer, db.ForeignKey("stores.id"), nullable=True
    )

    is_active = db.Column(db.Boolean, nullable=False, default=True)

    created_at = db.Column(db.DateTime, nullable=False, default=_utc_now)

    store = db.relationship("Store")

    redemptions = db.relationship(
        "CouponRedemption",
        back_populates="coupon",
        passive_deletes=True,
    )

    @property
    def is_platform_wide(self):
        return self.store_id is None

    def to_dict(self):
        """Owner/admin view.

        There is no public serializer for a coupon: usage counts and limits
        are operator data, and nothing on a storefront needs them. A caller
        that only holds a code learns whether it works by asking
        ``POST /api/cart/coupon``.
        """
        return {
            "id": self.id,
            "code": self.code,
            "discount_type": self.discount_type,
            "value": float(self.value),
            "min_order_total": (
                float(self.min_order_total)
                if self.min_order_total is not None
                else None
            ),
            "starts_at": _utc_isoformat(self.starts_at),
            "ends_at": _utc_isoformat(self.ends_at),
            "usage_limit": self.usage_limit,
            "per_user_limit": self.per_user_limit,
            "used_count": self.used_count,
            "store_id": self.store_id,
            "is_active": self.is_active,
            "created_at": _utc_isoformat(self.created_at),
        }
