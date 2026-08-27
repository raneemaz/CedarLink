from datetime import datetime

from app.extensions import db


class PaymentMethod(db.Model):
    __tablename__ = "payment_methods"

    id = db.Column(
        db.Integer,
        primary_key=True
    )

    user_id = db.Column(
        db.Integer,
        db.ForeignKey("users.id"),
        nullable=False
    )

    # Saved payment methods are cards only.
    type = db.Column(
        db.String(30),
        nullable=False
    )

    # A user-provided name for the card, such as "Personal Visa".
    label = db.Column(
        db.String(100),
        nullable=False
    )

    # Card brand: Visa, Mastercard, etc.
    brand = db.Column(
        db.String(30),
        nullable=True
    )

    # Only the last four digits are stored for cards.
    last4 = db.Column(
        db.String(4),
        nullable=True
    )
    # Hash of the full card number.
    # The raw card number is never stored.
    number_hash = db.Column(
        db.String(255),
        nullable=True
    )

    # Provider information.
    # These are identifiers/tokens, NOT card numbers or CVV.
    provider = db.Column(
        db.String(50),
        nullable=True
    )

    provider_customer_id = db.Column(
        db.String(255),
        nullable=True
    )

    provider_payment_method_id = db.Column(
        db.String(255),
        nullable=True
    )

    is_default = db.Column(
        db.Boolean,
        nullable=False,
        default=False
    )

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
        back_populates="payment_methods"
    )

    def to_dict(self):
        return {
            "id": self.id,
            "type": self.type,
            "label": self.label,
            "brand": self.brand,
            "last4": self.last4,
            "provider": self.provider,
            "is_default": self.is_default,
            "created_at": (
                self.created_at.isoformat()
                if self.created_at
                else None
            ),
            "updated_at": (
                self.updated_at.isoformat()
                if self.updated_at
                else None
            ),
        }
