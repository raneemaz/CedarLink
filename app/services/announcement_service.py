"""Store announcements — validation, the live-window rule, and the active cap.

Routes parse the request and call in here; the model stays data-only. An
announcement is *live* when it is active and the current instant is inside
``[starts_at, ends_at)`` (``ends_at`` NULL = open-ended). Times are naive UTC,
consistent with the store-hours ADR (0013).
"""

from datetime import datetime, timezone

from app.extensions import db
from app.models.store_announcement import StoreAnnouncement

MAX_ACTIVE_PER_STORE = 5
TITLE_MAX = 255
BODY_MAX = 2000


class AnnouncementError(ValueError):
    """Invalid announcement input — the route returns it as 400."""


def _now():
    return datetime.now(timezone.utc).replace(tzinfo=None)


def _parse_dt(value, field):
    """A caller-supplied ISO 8601 string as naive UTC, or None."""
    if value is None:
        return None
    if not isinstance(value, str) or not value.strip():
        raise AnnouncementError(f"{field} must be an ISO 8601 timestamp")

    text = value.strip().replace("Z", "+00:00")
    try:
        parsed = datetime.fromisoformat(text)
    except ValueError:
        raise AnnouncementError(f"{field} is not a valid ISO 8601 timestamp")

    if parsed.tzinfo is not None:
        parsed = parsed.astimezone(timezone.utc).replace(tzinfo=None)
    return parsed


def is_live(announcement, now=None):
    """Whether an announcement should currently show on the storefront."""
    if not announcement.is_active:
        return False
    now = now or _now()
    if announcement.starts_at and announcement.starts_at > now:
        return False
    if announcement.ends_at and announcement.ends_at <= now:
        return False
    return True


def serialize(announcement, now=None):
    """``to_dict`` plus the derived ``is_live`` flag (for owner-facing lists)."""
    return {**announcement.to_dict(), "is_live": is_live(announcement, now)}


def live_for_store(store, now=None):
    """The store's live announcements, newest first (relationship order)."""
    now = now or _now()
    return [a for a in store.announcements if is_live(a, now)]


def _validated_fields(data, *, partial, existing=None):
    fields = {}

    if "title" in data or not partial:
        title = (data.get("title") or "").strip()
        if not title:
            raise AnnouncementError("title is required")
        if len(title) > TITLE_MAX:
            raise AnnouncementError(
                f"title must be {TITLE_MAX} characters or fewer"
            )
        fields["title"] = title

    if "body" in data or not partial:
        body = (data.get("body") or "").strip()
        if not body:
            raise AnnouncementError("body is required")
        if len(body) > BODY_MAX:
            raise AnnouncementError(
                f"body must be {BODY_MAX} characters or fewer"
            )
        fields["body"] = body

    if "starts_at" in data:
        fields["starts_at"] = _parse_dt(data.get("starts_at"), "starts_at")
        if fields["starts_at"] is None:
            fields["starts_at"] = _now()
    if "ends_at" in data:
        fields["ends_at"] = _parse_dt(data.get("ends_at"), "ends_at")

    if "is_active" in data:
        if not isinstance(data["is_active"], bool):
            raise AnnouncementError("is_active must be true or false")
        fields["is_active"] = data["is_active"]

    starts = fields.get("starts_at", getattr(existing, "starts_at", None))
    ends = fields.get("ends_at", getattr(existing, "ends_at", None))
    if starts and ends and ends <= starts:
        raise AnnouncementError("ends_at must be after starts_at")

    return fields


def _assert_active_cap(store, *, becoming_active, exclude_id=None):
    if not becoming_active:
        return
    active = sum(
        1
        for a in store.announcements
        if a.is_active and a.id != exclude_id
    )
    if active >= MAX_ACTIVE_PER_STORE:
        raise AnnouncementError(
            "a store may have at most "
            f"{MAX_ACTIVE_PER_STORE} active announcements"
        )


def create(store, data):
    """Validate and add a new announcement. Caller commits."""
    if not isinstance(data, dict):
        raise AnnouncementError("request body must be a JSON object")

    fields = _validated_fields(data, partial=False)
    fields.setdefault("starts_at", _now())
    _assert_active_cap(store, becoming_active=fields.get("is_active", True))

    announcement = StoreAnnouncement(store_id=store.id, **fields)
    db.session.add(announcement)
    db.session.flush()
    return announcement


def update(store, announcement, data):
    """Validate and apply a partial update. Caller commits."""
    if not isinstance(data, dict):
        raise AnnouncementError("request body must be a JSON object")

    fields = _validated_fields(data, partial=True, existing=announcement)
    _assert_active_cap(
        store,
        becoming_active=fields.get("is_active", announcement.is_active),
        exclude_id=announcement.id,
    )

    for key, value in fields.items():
        setattr(announcement, key, value)
    return announcement


def delete(announcement):
    """Remove an announcement. Caller commits."""
    db.session.delete(announcement)
