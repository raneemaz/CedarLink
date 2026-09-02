from datetime import datetime, timezone

from app.extensions import db


def _utc_now_naive():
    """Current UTC as a naive datetime — the storage convention in this schema.

    ``datetime.now(timezone.utc)`` (never ``utcnow()``), tz dropped for the
    column, consistent with ``Store.override_until`` and the store-hours ADR.
    """
    return datetime.now(timezone.utc).replace(tzinfo=None)


def _utc_isoformat(value):
    """A stored naive-UTC datetime as an explicit-UTC ISO 8601 string."""
    if value is None:
        return None
    if value.tzinfo is None:
        value = value.replace(tzinfo=timezone.utc)
    return value.isoformat()


class StoreAnnouncement(db.Model):
    """A vendor notice shown on the store page while active and in its window.

    ``starts_at`` / ``ends_at`` are naive UTC like every other timestamp in
    this schema (see docs/decisions/0013-store-hours-timezone.md). Whether an
    announcement is *live* — ``is_active`` and ``starts_at <= now`` and
    (``ends_at`` is NULL or ``now < ends_at``) — is decided in
    ``announcement_service``, the one place that owns that rule.

    There is deliberately no ORM cascade: the store is soft-deleted, never
    row-deleted, so these rows persist with it — the same call the ``hours``
    relationship makes in ``store.py``.
    """

    __tablename__ = "store_announcements"

    id = db.Column(db.Integer, primary_key=True)

    store_id = db.Column(
        db.Integer,
        db.ForeignKey("stores.id"),
        nullable=False,
        index=True,
    )

    title = db.Column(db.String(255), nullable=False)
    body = db.Column(db.Text, nullable=False)

    starts_at = db.Column(db.DateTime, nullable=False, default=_utc_now_naive)
    ends_at = db.Column(db.DateTime, nullable=True)

    is_active = db.Column(
        db.Boolean,
        nullable=False,
        default=True,
        server_default=db.true(),
    )

    created_at = db.Column(
        db.DateTime,
        nullable=False,
        default=_utc_now_naive,
        index=True,
    )

    store = db.relationship("Store", back_populates="announcements")

    def to_dict(self):
        return {
            "id": self.id,
            "store_id": self.store_id,
            "title": self.title,
            "body": self.body,
            "starts_at": _utc_isoformat(self.starts_at),
            "ends_at": _utc_isoformat(self.ends_at),
            "is_active": self.is_active,
            "created_at": _utc_isoformat(self.created_at),
        }

    def __repr__(self):
        return (
            f"<StoreAnnouncement store={self.store_id} "
            f"{self.title!r} active={self.is_active}>"
        )
