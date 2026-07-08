from datetime import datetime
from app.extensions import db


class DeliveryAssignment(db.Model):
    __tablename__ = "delivery_assignments"

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

    driver_name = db.Column(
        db.String(120),
        nullable=False
    )

    driver_phone = db.Column(
        db.String(30),
        nullable=False
    )

    status = db.Column(
        db.String(30),
        nullable=False,
        default="assigned"
    )

    assigned_at = db.Column(
        db.DateTime,
        nullable=False,
        default=datetime.utcnow
    )

    delivered_at = db.Column(
        db.DateTime,
        nullable=True
    )

    order = db.relationship(
        "Order",
        backref=db.backref(
            "delivery_assignment",
            uselist=False,
            cascade="all, delete-orphan"
        )
    )

    def to_dict(self):
        return {
            "id": self.id,
            "order_id": self.order_id,
            "driver_name": self.driver_name,
            "driver_phone": self.driver_phone,
            "status": self.status,
            "assigned_at": (
                self.assigned_at.isoformat()
                if self.assigned_at
                else None
            ),
            "delivered_at": (
                self.delivered_at.isoformat()
                if self.delivered_at
                else None
            )
        }
