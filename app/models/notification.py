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
    __table_args__ = (
        # The list endpoint runs WHERE user_id = X ORDER BY created_at DESC;
        # the unread count runs WHERE user_id = X AND is_read = false. Both
        # need a user_id-leading composite — a standalone index on either
        # trailing column cannot serve that access path. Migration
        # c4a9e7f2105d created these; the model just never declared them.
        # See docs/decisions/0016-model-migration-drift-guard.md.
        db.Index(
            "ix_notifications_user_created_at", "user_id", "created_at"
        ),
        db.Index("ix_notifications_user_is_read", "user_id", "is_read"),
    )

    id = db.Column(db.Integer, primary_key=True)

    # ix_notifications_user_id: kept although it is now a redundant leading
    # prefix of both composites above. Dropping it would turn this
    # model-only fix into a database migration for no measurable gain.
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
