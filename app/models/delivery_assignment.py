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

    def to_dict(self, include_driver_phone=False):
        # driver_phone is a third party's personal number. It is NOT in the
        # base payload; callers opt in: the vendor always, the customer only
        # while the delivery is in progress (see delivery_routes). ADR 0019.
        payload = {
            "id": self.id,
            "order_id": self.order_id,
            "driver_name": self.driver_name,
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
        if include_driver_phone:
            payload["driver_phone"] = self.driver_phone
        return payload
