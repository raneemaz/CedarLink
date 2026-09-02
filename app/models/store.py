from datetime import timezone

from sqlalchemy import and_
from sqlalchemy.ext.hybrid import hybrid_property

from app.extensions import db


def _utc_isoformat(value):
    """A stored naive-UTC datetime as an explicit-UTC ISO 8601 string."""
    if value is None:
        return None
    if value.tzinfo is None:
        value = value.replace(tzinfo=timezone.utc)
    return value.isoformat()


class Store(db.Model):
    __tablename__ = "stores"
    __table_args__ = (
        # Distance search does a BETWEEN on both columns as its first pass;
        # the composite index makes that a range scan. See
        # docs/decisions/0018-location-and-distance-search.md.
        db.Index("ix_stores_lat_lng", "latitude", "longitude"),
    )

    id = db.Column(db.Integer, primary_key=True)

    owner_id = db.Column(
        db.Integer,
        db.ForeignKey("users.id"),
        nullable=False
    )

    name = db.Column(db.String(120), nullable=False)

    description = db.Column(db.Text)

    location = db.Column(db.String(255))

    contact_info = db.Column(db.String(255))

    is_active = db.Column(
        db.Boolean,
        default=True,
        nullable=False
    )

    inside_city_delivery_fee = db.Column(
        db.Numeric(10, 2),
        nullable=False,
        default=0.00
    )

    outside_city_delivery_fee = db.Column(
        db.Numeric(10, 2),
        nullable=False,
        default=0.00
    )

    delivery_available = db.Column(
        db.Boolean,
        default=True,
        nullable=False
    )

    # Set when an admin removes the store. See
    # docs/decisions/0004-soft-delete-stores.md.
    deleted_at = db.Column(db.DateTime, nullable=True)

    # Admin approval gate. New stores start "pending" and are invisible to
    # customers until approved. See
    # docs/decisions/0005-vendor-registration-and-store-approval.md.
    approval_status = db.Column(
        db.String(20),
        nullable=False,
        default="pending",
        server_default="pending",
    )
    approval_note = db.Column(db.String(255), nullable=True)

    # Manual open/closed override. Wins over the weekly schedule while
    # override_until is in the future; ignored (not mutated) once it passes.
    # override_status is "open" or "closed". override_until is naive UTC, like
    # every other timestamp in this schema. See
    # docs/decisions/0013-store-hours-timezone.md.
    override_status = db.Column(db.String(10), nullable=True)
    override_reason = db.Column(db.String(255), nullable=True)
    override_until = db.Column(db.DateTime, nullable=True)

    # Denormalized rating aggregates, recomputed from the published reviews
    # by review_service — never incremented. See
    # docs/decisions/0015-review-rating-aggregates.md.
    rating_avg = db.Column(db.Numeric(3, 2), nullable=True)
    rating_count = db.Column(db.Integer, nullable=False, default=0,
                             server_default="0")

    # Map pin. Nullable — existing stores have none and a store without a
    # pin must keep working everywhere; it is simply absent from distance
    # results. Set together or not at all (store_service.set_location).
    latitude = db.Column(db.Numeric(9, 6), nullable=True)
    longitude = db.Column(db.Numeric(9, 6), nullable=True)

    # An online-only store has no shopfront: it never carries coordinates
    # and never appears in a distance search (store_service.set_online_only).
    is_online_only = db.Column(
        db.Boolean, nullable=False, default=False, server_default=db.false()
    )

    owner = db.relationship(
        "User",
        back_populates="stores"
    )

    # No delete-orphan on products or orders: removing a store must not
    # destroy customers' order history (CL-24). Products are already
    # soft-deleted (CL-23); the store's removal hides the rest.
    products = db.relationship(
        "Product",
        back_populates="store"
    )

    orders = db.relationship(
        "Order",
        back_populates="store"
    )

    # No cascade: the store is soft-deleted (deleted_at), never row-deleted,
    # so these rows persist with it. A soft-deleted store is not is_visible
    # and is therefore never "open" regardless of its hours. PUT /hours
    # replaces the week with an explicit delete + insert in one transaction.
    hours = db.relationship(
        "StoreHours",
        back_populates="store",
        order_by="StoreHours.day_of_week, StoreHours.opens_at",
    )

    # No cascade, for the same reason as hours above: the store is
    # soft-deleted, never row-deleted, so these rows persist with it.
    announcements = db.relationship(
        "StoreAnnouncement",
        back_populates="store",
        order_by="StoreAnnouncement.created_at.desc()",
    )

    # No cascade: a store review outlives the store's soft-delete, like
    # order history. See docs/decisions/0015-review-rating-aggregates.md.
    reviews = db.relationship(
        "Review",
        back_populates="store",
    )

    @hybrid_property
    def is_visible(self):
        """Shown on the storefront: approved by an admin, active, not removed.

        One definition, usable both as ``store.is_visible`` in Python and as
        ``Store.is_visible`` inside a ``filter()`` (see the ``.expression``
        below). It is a security-relevant rule — keep it in exactly one place.
        """
        return (
            self.approval_status == "approved"
            and self.is_active
            and self.deleted_at is None
        )

    @is_visible.expression
    def is_visible(cls):
        return and_(
            cls.approval_status == "approved",
            cls.is_active.is_(True),
            cls.deleted_at.is_(None),
        )

    def to_dict(self):
        # A public serializer is an allowlist, not a dump. approval_note is
        # an admin-authored note and is added back only on the owner /
        # admin routes (store_service.owner_store_dict, admin_routes). See
        # CLAUDE.md. Other fields here (owner_id, approval_status,
        # deleted_at) are flagged for a later, wider allowlist pass.
        return {
            "id": self.id,
            "owner_id": self.owner_id,
            "name": self.name,
            "description": self.description,
            "location": self.location,
            "contact_info": self.contact_info,
            "is_active": self.is_active,
            "deleted_at": _utc_isoformat(self.deleted_at),
            "approval_status": self.approval_status,
            "inside_city_delivery_fee": float(self.inside_city_delivery_fee
                                              or 0),
            "outside_city_delivery_fee": float(self.outside_city_delivery_fee
                                               or 0),
            "delivery_available": self.delivery_available,
            "override_status": self.override_status,
            "override_reason": self.override_reason,
            "override_until": _utc_isoformat(self.override_until),
            "rating_avg": (
                float(self.rating_avg) if self.rating_avg is not None else None
            ),
            "rating_count": self.rating_count or 0,
            "latitude": (
                float(self.latitude) if self.latitude is not None else None
            ),
            "longitude": (
                float(self.longitude) if self.longitude is not None else None
            ),
            "is_online_only": bool(self.is_online_only),
        }
