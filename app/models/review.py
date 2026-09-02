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


class Review(db.Model):
    """A verified-purchase rating of one product **or** one store.

    Exactly one of ``product_id`` / ``store_id`` is set — enforced by a CHECK
    constraint, because a review with both or neither is meaningless. The
    verified-purchase rule (delivered order, owned by the reviewer, actually
    containing the target) lives in ``review_service``.

    Two unique constraints, not one: ``NULL != NULL`` in SQL means a single
    ``(user_id, order_id, product_id)`` index cannot see two store reviews
    (both with ``product_id`` NULL) as a collision, and vice versa.

    No cascade from Order, Product or Store: a review outlives a
    soft-deleted product the same way an order item does. See
    docs/decisions/0015-review-rating-aggregates.md.
    """

    __tablename__ = "reviews"
    __table_args__ = (
        db.CheckConstraint(
            "(product_id IS NOT NULL AND store_id IS NULL) OR "
            "(product_id IS NULL AND store_id IS NOT NULL)",
            name="ck_reviews_exactly_one_target",
        ),
        db.CheckConstraint(
            "rating >= 1 AND rating <= 5",
            name="ck_reviews_rating_range",
        ),
        db.UniqueConstraint(
            "user_id", "order_id", "product_id",
            name="uq_reviews_user_order_product",
        ),
        db.UniqueConstraint(
            "user_id", "order_id", "store_id",
            name="uq_reviews_user_order_store",
        ),
        db.Index("ix_reviews_product_id", "product_id"),
        db.Index("ix_reviews_store_id", "store_id"),
    )

    id = db.Column(db.Integer, primary_key=True)

    user_id = db.Column(
        db.Integer, db.ForeignKey("users.id"), nullable=False, index=True
    )
    order_id = db.Column(
        db.Integer, db.ForeignKey("orders.id"), nullable=False
    )

    product_id = db.Column(
        db.Integer, db.ForeignKey("products.id"), nullable=True
    )
    store_id = db.Column(
        db.Integer, db.ForeignKey("stores.id"), nullable=True
    )

    rating = db.Column(db.SmallInteger, nullable=False)
    title = db.Column(db.String(120), nullable=True)
    body = db.Column(db.Text, nullable=True)

    # published (default) / flagged / removed. published and flagged both
    # count toward a rating and stay publicly visible; only 'removed' is
    # hidden and de-counted. See docs/decisions/0017-review-moderation.md.
    status = db.Column(
        db.String(20),
        nullable=False,
        default="published",
        server_default="published",
    )

    # The reason recorded on the last admin remove / restore.
    moderation_note = db.Column(db.String(500), nullable=True)

    created_at = db.Column(db.DateTime, nullable=False, default=_utc_now)
    updated_at = db.Column(
        db.DateTime, nullable=False, default=_utc_now, onupdate=_utc_now
    )

    user = db.relationship("User", back_populates="reviews")
    order = db.relationship("Order", back_populates="reviews")
    product = db.relationship("Product", back_populates="reviews")
    store = db.relationship("Store", back_populates="reviews")

    # Reports are evidence — they outlive moderation. delete-orphan only
    # fires if the author deletes their own review, taking its reports with
    # it (nothing to moderate once the review is gone).
    reports = db.relationship(
        "ReviewReport",
        back_populates="review",
        cascade="all, delete-orphan",
        order_by="ReviewReport.created_at.desc()",
    )

    def to_dict(self):
        return {
            "id": self.id,
            "user_id": self.user_id,
            "order_id": self.order_id,
            "product_id": self.product_id,
            "store_id": self.store_id,
            "rating": self.rating,
            "title": self.title,
            "body": self.body,
            "status": self.status,
            "moderation_note": self.moderation_note,
            "author_name": (
                self.user.first_name if self.user else None
            ),
            "created_at": _utc_isoformat(self.created_at),
            "updated_at": _utc_isoformat(self.updated_at),
        }

    def __repr__(self):
        target = (
            f"product={self.product_id}"
            if self.product_id
            else f"store={self.store_id}"
        )
        return f"<Review {self.id} {target} rating={self.rating}>"
