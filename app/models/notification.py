from datetime import datetime, timezone

from app.extensions import db


def _utc_isoformat(value):
    """Serialize a stored datetime as an explicit-UTC ISO 8601 string.

    ``created_at`` / ``read_at`` are written with ``datetime.utcnow`` and are
    therefore naive values that represent UTC. Emitting them without a timezone
    designator makes browsers parse them as *local* time; annotating them as
    UTC (``...+00:00``) makes ``new Date(...)`` unambiguous.
    """
    if value is None:
        return None

    if value.tzinfo is None:
        value = value.replace(tzinfo=timezone.utc)

    return value.isoformat()


class Notification(db.Model):
    __tablename__ = "notifications"

    id = db.Column(db.Integer, primary_key=True)

    user_id = db.Column(
        db.Integer,
        db.ForeignKey("users.id"),
        nullable=False,
        index=True,
    )

    # Preference category this notification belongs to. Must match one of
    # notification_service.CATEGORIES so should_notify() can gate it.
    category = db.Column(db.String(50), nullable=False)

    # Specific event key, e.g. "order_placed", "order_status_changed",
    # "order_canceled", "payment_completed", "payment_refunded",
    # "delivery_update".
    type = db.Column(db.String(50), nullable=False)

    title = db.Column(db.String(255), nullable=False)

    message = db.Column(db.String(500), nullable=False)

    # Optional frontend navigation target, e.g. "/orders/42".
    link = db.Column(db.String(255), nullable=True)

    is_read = db.Column(
        db.Boolean,
        nullable=False,
        default=False,
        server_default=db.false(),
    )

    read_at = db.Column(db.DateTime, nullable=True)

    created_at = db.Column(
        db.DateTime,
        nullable=False,
        default=datetime.utcnow,
        index=True,
    )

    user = db.relationship(
        "User",
        back_populates="notifications",
    )

    def to_dict(self):
        return {
            "id": self.id,
            "category": self.category,
            "type": self.type,
            "title": self.title,
            "message": self.message,
            "link": self.link,
            "is_read": self.is_read,
            "read_at": _utc_isoformat(self.read_at),
            "created_at": _utc_isoformat(self.created_at),
        }
