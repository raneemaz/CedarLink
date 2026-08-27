from datetime import datetime

from app.extensions import db


class Payment(db.Model):
    __tablename__ = "payments"

    id = db.Column(
        db.Integer,
        primary_key=True
    )

    order_id = db.Column(
        db.Integer,
        db.ForeignKey("orders.id"),
        nullable=False,
        unique=True
    )

    amount = db.Column(
        db.Numeric(10, 2),
        nullable=False
    )

    # card / cash_on_delivery
    method = db.Column(
        db.String(50),
        nullable=False
    )

    # Actual provider handling the payment.
    # Examples: a card processor or cedarlink for cash on delivery.
    provider = db.Column(
        db.String(50),
        nullable=False
    )

    # Reference returned by the payment provider.
    provider_payment_id = db.Column(
        db.String(255),
        nullable=True
    )

    status = db.Column(
        db.String(20),
        nullable=False,
        default="pending"
    )

    transaction_id = db.Column(
        db.String(255),
        unique=True,
        nullable=True
    )

    # Optional reference to a saved payment method.
    payment_method_id = db.Column(
        db.Integer,
        db.ForeignKey("payment_methods.id"),
        nullable=True
    )

    created_at = db.Column(
        db.DateTime,
        nullable=False,
        default=datetime.utcnow
    )

    updated_at = db.Column(
        db.DateTime,
        nullable=False,
        default=datetime.utcnow,
        onupdate=datetime.utcnow
    )

    order = db.relationship(
        "Order",
        back_populates="payments"
    )

    payment_method = db.relationship(
        "PaymentMethod"
    )

    def to_dict(self):
        return {
            "id": self.id,
            "order_id": self.order_id,
            "amount": float(self.amount),
            "method": self.method,
            "provider": self.provider,
            "provider_payment_id": self.provider_payment_id,
            "payment_method_id": self.payment_method_id,
            "status": self.status,
            "transaction_id": self.transaction_id,
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
