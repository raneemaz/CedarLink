from sqlalchemy import and_
from sqlalchemy.ext.hybrid import hybrid_property

from app.extensions import db


class Store(db.Model):
    __tablename__ = "stores"

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
        return {
            "id": self.id,
            "owner_id": self.owner_id,
            "name": self.name,
            "description": self.description,
            "location": self.location,
            "contact_info": self.contact_info,
            "is_active": self.is_active,
            "deleted_at": (
                self.deleted_at.isoformat() if self.deleted_at else None
            ),
            "approval_status": self.approval_status,
            "approval_note": self.approval_note,
            "inside_city_delivery_fee": float(self.inside_city_delivery_fee
                                              or 0),
            "outside_city_delivery_fee": float(self.outside_city_delivery_fee
                                               or 0),
            "delivery_available": self.delivery_available,
        }
