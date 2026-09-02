from datetime import datetime

from app.extensions import db


class Address(db.Model):
    __tablename__ = "addresses"

    id = db.Column(
        db.Integer,
        primary_key=True
    )

    user_id = db.Column(
        db.Integer,
        db.ForeignKey("users.id"),
        nullable=False
    )

    label = db.Column(
        db.String(50),
        nullable=False
    )

    recipient_name = db.Column(
        db.String(100),
        nullable=False
    )

    phone = db.Column(
        db.String(20),
        nullable=False
    )

    address_line = db.Column(
        db.String(255),
        nullable=False
    )

    city = db.Column(
        db.String(100),
        nullable=False
    )

    delivery_instructions = db.Column(
        db.String(500),
        nullable=True
    )

    is_default = db.Column(
        db.Boolean,
        nullable=False,
        default=False
    )

    # Optional map pin for the delivery address — same types and validation
    # as Store. Nullable: addresses saved before this feature have none and
    # must keep working. See docs/decisions/0018-location-and-distance-search.md.
    latitude = db.Column(db.Numeric(9, 6), nullable=True)
    longitude = db.Column(db.Numeric(9, 6), nullable=True)

    created_at = db.Column(
        db.DateTime,
        default=datetime.utcnow,
        nullable=False
    )

    updated_at = db.Column(
        db.DateTime,
        default=datetime.utcnow,
        onupdate=datetime.utcnow,
        nullable=False
    )

    user = db.relationship(
        "User",
        back_populates="addresses"
    )
