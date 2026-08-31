"""Store availability — the single source of truth for 'is this store open'.

Nothing else in the codebase decides open/closed. Routes and other services
call :func:`is_open_now`; the order service turns a closed result into the
standard ``OrderError`` at cart-add and checkout.

Time handling: the current instant is resolved in the ``Asia/Beirut`` zone
via :class:`zoneinfo.ZoneInfo`, so DST (EET/EEST) is applied automatically —
never a fixed offset, never ``datetime.utcnow()``. ``StoreHours`` times are
naive local wall-clock; ``Store.override_until`` is naive UTC like every
other timestamp. See docs/decisions/0013-store-hours-timezone.md.
"""

from datetime import datetime, timedelta, timezone
from zoneinfo import ZoneInfo

from app.extensions import db
from app.models.store_hours import StoreHours

BEIRUT = ZoneInfo("Asia/Beirut")

OVERRIDE_MAX_DAYS = 7

# Second element of the is_open_now() tuple.
OPEN_OVERRIDE = "override_open"
OPEN_SCHEDULED = "scheduled"
CLOSED_NOT_VISIBLE = "not_visible"
CLOSED_OVERRIDE = "override_closed"
CLOSED_OUTSIDE_HOURS = "outside_hours"

OVERRIDE_STATUSES = ("open", "closed")


class StoreHoursError(ValueError):
    """Invalid working-hours / override input — the route returns it as 400."""


def _now_local():
    """Current wall-clock time in Beirut. The single seam tests patch."""
    return datetime.now(BEIRUT)


def _now_utc():
    return datetime.now(timezone.utc)


def _as_beirut(at):
    """Coerce a caller-supplied instant to an aware Beirut datetime.

    A naive value is read as Beirut local time (that is what a test writing
    ``datetime(2026, 1, 5, 1, 0)`` means).
    """
    if at.tzinfo is None:
        return at.replace(tzinfo=BEIRUT)
    return at.astimezone(BEIRUT)


def _override_status(store, now_utc):
    """The active override status, or None when there is none / it expired.

    The row is never mutated here — an expired override is simply ignored and
    the schedule decides.
    """
    if store.override_status not in OVERRIDE_STATUSES:
        return None
    if store.override_until is None:
        return None

    until = store.override_until
    if until.tzinfo is None:
        until = until.replace(tzinfo=timezone.utc)

    if until <= now_utc:
        return None
    return store.override_status


def _row_covers(row, weekday, local_time):
    """Does one StoreHours row cover (weekday, local_time)?

    ``opens_at < closes_at``  -> a same-day interval ``[opens, closes)``.
    ``closes_at <= opens_at`` -> the interval crosses midnight: the evening
    part ``[opens, 24:00)`` sits on the row's own day, the morning part
    ``[00:00, closes)`` on the following day.
    """
    opens, closes = row.opens_at, row.closes_at

    if opens < closes:
        return row.day_of_week == weekday and opens <= local_time < closes

    if row.day_of_week == weekday and local_time >= opens:
        return True
    if row.day_of_week == (weekday - 1) % 7 and local_time < closes:
        return True
    return False


def is_open_now(store, at=None):
    """Return ``(is_open: bool, reason_code: str)``.

    ``at`` freezes the moment for tests — an aware datetime in any zone, or a
    naive one read as Beirut local. Production passes nothing.
    """
    if not store.is_visible:
        return False, CLOSED_NOT_VISIBLE

    local = _as_beirut(at) if at is not None else _now_local()
    now_utc = local.astimezone(timezone.utc)

    override = _override_status(store, now_utc)
    if override == "open":
        return True, OPEN_OVERRIDE
    if override == "closed":
        return False, CLOSED_OVERRIDE

    weekday = local.weekday()          # Monday = 0
    local_time = local.time()

    for row in store.hours:
        if _row_covers(row, weekday, local_time):
            return True, OPEN_SCHEDULED

    return False, CLOSED_OUTSIDE_HOURS


# --------------------------------------------------------------------------- #
# Writes — hours and override
# --------------------------------------------------------------------------- #

def _parse_time(value):
    if not isinstance(value, str):
        raise StoreHoursError("opens_at / closes_at must be 'HH:MM' strings")
    for fmt in ("%H:%M", "%H:%M:%S"):
        try:
            return datetime.strptime(value, fmt).time()
        except ValueError:
            continue
    raise StoreHoursError(f"'{value}' is not a valid time")


def _minutes(t):
    return t.hour * 60 + t.minute


def replace_hours(store, entries):
    """Validate ``entries`` and replace the store's whole week.

    ``entries`` — list of ``{"day_of_week": 0-6, "opens_at": "HH:MM",
    "closes_at": "HH:MM"}``. Monday = 0. A day may repeat (several intervals);
    two intervals on the same day may not overlap. ``closes_at`` at or before
    ``opens_at`` means the interval crosses midnight.

    Deletes the existing rows and inserts the new ones in the caller's
    transaction. Raises :class:`StoreHoursError` on any invalid entry.
    """
    if not isinstance(entries, list):
        raise StoreHoursError("hours must be a list")

    parsed = []
    for entry in entries:
        if not isinstance(entry, dict):
            raise StoreHoursError("each hours entry must be an object")

        day = entry.get("day_of_week")
        if not isinstance(day, int) or isinstance(day, bool) or not 0 <= day <= 6:
            raise StoreHoursError("day_of_week must be an integer 0-6")

        opens = _parse_time(entry.get("opens_at"))
        closes = _parse_time(entry.get("closes_at"))
        if opens == closes:
            raise StoreHoursError(
                "opens_at and closes_at must differ"
            )

        parsed.append((day, opens, closes))

    _assert_no_overlap(parsed)

    StoreHours.query.filter_by(store_id=store.id).delete(
        synchronize_session=False
    )
    for day, opens, closes in parsed:
        db.session.add(
            StoreHours(
                store_id=store.id,
                day_of_week=day,
                opens_at=opens,
                closes_at=closes,
            )
        )


def _assert_no_overlap(parsed):
    """No two intervals on the same weekday may overlap.

    Each interval is projected onto its own day: a same-day interval is
    ``[opens, closes)``; a midnight-crossing one is ``[opens, 24:00)`` (its
    spill into the next day is a different weekday and is not checked here).
    Touching endpoints (``12:00`` close, ``12:00`` open) do not overlap.
    """
    by_day = {}
    for day, opens, closes in parsed:
        start = _minutes(opens)
        end = _minutes(closes) if opens < closes else 24 * 60
        by_day.setdefault(day, []).append((start, end))

    for day, spans in by_day.items():
        spans.sort()
        for (_, prev_end), (next_start, _) in zip(spans, spans[1:]):
            if next_start < prev_end:
                raise StoreHoursError(
                    f"overlapping opening hours on day {day}"
                )


def _coerce_until(value):
    if not isinstance(value, str) or not value.strip():
        raise StoreHoursError("until is required")

    text = value.strip().replace("Z", "+00:00")
    try:
        parsed = datetime.fromisoformat(text)
    except ValueError:
        raise StoreHoursError("until is not a valid ISO 8601 timestamp")

    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=timezone.utc)
    return parsed.astimezone(timezone.utc)


def set_override(store, status, reason, until):
    """Apply a manual override. Caller commits.

    Rejects a status other than open/closed, a missing/past ``until``, and an
    ``until`` more than :data:`OVERRIDE_MAX_DAYS` days ahead.
    """
    if status not in OVERRIDE_STATUSES:
        raise StoreHoursError("status must be 'open' or 'closed'")

    until_utc = _coerce_until(until)
    now = _now_utc()

    if until_utc <= now:
        raise StoreHoursError("until must be in the future")
    if until_utc > now + timedelta(days=OVERRIDE_MAX_DAYS):
        raise StoreHoursError(
            f"until cannot be more than {OVERRIDE_MAX_DAYS} days ahead"
        )

    reason = (reason or "").strip() or None
    if reason and len(reason) > 255:
        raise StoreHoursError("reason must be 255 characters or fewer")

    store.override_status = status
    store.override_reason = reason
    store.override_until = until_utc.replace(tzinfo=None)


def clear_override(store):
    """Remove any override. Caller commits."""
    store.override_status = None
    store.override_reason = None
    store.override_until = None
