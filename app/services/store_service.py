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

import math
from datetime import datetime, timedelta, timezone
from decimal import Decimal
from zoneinfo import ZoneInfo

from app.extensions import db
from app.models.store import Store
from app.models.store_hours import StoreHours
from app.utils.geo import (
    CoordinateError,
    KM_PER_DEG_LAT,
    haversine_km,
    validate_coords,
)

BEIRUT = ZoneInfo("Asia/Beirut")

OVERRIDE_MAX_DAYS = 7

# Second element of the is_open_now() tuple.
OPEN_OVERRIDE = "override_open"
OPEN_SCHEDULED = "scheduled"
CLOSED_NOT_VISIBLE = "not_visible"
CLOSED_OVERRIDE = "override_closed"
CLOSED_OUTSIDE_HOURS = "outside_hours"

OVERRIDE_STATUSES = ("open", "closed")

# Accepted values for the override `duration` field. Everything but "custom"
# is a named preset resolved server-side against Beirut local time — the
# browser's zone is not necessarily Lebanon's (ADR 0013).
OVERRIDE_DURATIONS = ("1h", "3h", "end_of_day", "tomorrow_morning", "custom")

# Local wall-clock time the "tomorrow_morning" preset resolves to.
TOMORROW_MORNING_HOUR = 8


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


def _schedule_covers(store, local):
    """Does the weekly schedule cover this Beirut instant? Override ignored."""
    weekday = local.weekday()
    local_time = local.time()
    return any(
        _row_covers(row, weekday, local_time) for row in store.hours
    )


def next_opening_time(store, at=None):
    """The next instant the store opens, as an aware Beirut datetime.

    ``None`` when the store has no hours at all — a store with an empty
    schedule is never open, so there is no answer to give rather than a
    misleading one.

    Two constraints, and the store opens at the **later** of them:

    * the weekly schedule, with the same edge cases ``is_open_now``
      handles — a split day has two intervals, and an interval whose
      ``closes_at`` is at or before its ``opens_at`` runs past midnight
      into the next day;
    * an active *closed* override, which holds the store shut until it
      expires even during scheduled hours. An override expiring at 14:00
      on a day the store is scheduled 09:00-20:00 means it opens at
      14:00, not 09:00.

    An *open* override is not consulted: the store is open now, so the
    answer is now.

    Looks ahead seven days and gives up after that. A weekly schedule with
    any row in it always opens inside seven days, so the cap only bites on
    data that could not open anyway.
    """
    if not store.hours:
        return None

    local = _as_beirut(at) if at is not None else _now_local()
    now_utc = local.astimezone(timezone.utc)

    # A closed override postpones the answer to at least its expiry.
    if _override_status(store, now_utc) == "closed":
        until = store.override_until
        if until.tzinfo is None:
            until = until.replace(tzinfo=timezone.utc)
        expiry_local = until.astimezone(BEIRUT)
        if expiry_local > local:
            local = expiry_local

    # Already inside an open interval at that moment — including the
    # morning half of an interval that began the previous evening.
    if _schedule_covers(store, local):
        return local

    horizon = local + timedelta(days=OVERRIDE_MAX_DAYS)
    best = None

    # Candidate openings are each row's opens_at on each day the row
    # applies to. The morning half of a midnight-crossing interval is a
    # continuation, not a fresh opening, so it is deliberately not a
    # candidate.
    for offset in range(OVERRIDE_MAX_DAYS + 1):
        day = (local + timedelta(days=offset)).date()

        for row in store.hours:
            if row.day_of_week != day.weekday():
                continue

            candidate = datetime.combine(
                day, row.opens_at, tzinfo=BEIRUT
            )

            if candidate < local or candidate > horizon:
                continue
            if best is None or candidate < best:
                best = candidate

    return best


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


def _resolve_override_until(duration, until):
    """The override end instant as aware UTC.

    Named durations are resolved here, not in the browser, so "end of day"
    and "tomorrow morning" always mean Beirut wall-clock regardless of the
    caller's timezone (ADR 0013). ``custom`` — and an omitted duration, for
    backward compatibility — carries an explicit ISO instant in ``until``.
    """
    if duration in (None, "custom"):
        return _coerce_until(until)

    if duration == "1h":
        return _now_utc() + timedelta(hours=1)
    if duration == "3h":
        return _now_utc() + timedelta(hours=3)

    now_local = _now_local()
    if duration == "end_of_day":
        end = now_local.replace(
            hour=23, minute=59, second=0, microsecond=0
        )
        return end.astimezone(timezone.utc)
    if duration == "tomorrow_morning":
        morning = (now_local + timedelta(days=1)).replace(
            hour=TOMORROW_MORNING_HOUR,
            minute=0,
            second=0,
            microsecond=0,
        )
        return morning.astimezone(timezone.utc)

    raise StoreHoursError(
        "duration must be one of " + ", ".join(OVERRIDE_DURATIONS)
    )


def set_override(store, status, reason, duration=None, until=None):
    """Apply a manual override. Caller commits.

    ``duration`` is one of :data:`OVERRIDE_DURATIONS`; ``until`` carries the
    explicit ISO instant when ``duration`` is ``"custom"`` (or omitted).
    Rejects a status other than open/closed, a resolved end that is in the
    past, and one more than :data:`OVERRIDE_MAX_DAYS` days ahead.
    """
    if status not in OVERRIDE_STATUSES:
        raise StoreHoursError("status must be 'open' or 'closed'")

    until_utc = _resolve_override_until(duration, until)
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


def owner_store_dict(store):
    """Store payload for the owner (and admin): the public allowlist plus
    ``approval_note``, the admin's rejection/approval note, which the
    vendor is meant to read but the storefront must not. See CLAUDE.md."""
    return {**store.to_dict(), "approval_note": store.approval_note}


# --------------------------------------------------------------------------- #
# Location & distance search — see docs/decisions/0018.
# --------------------------------------------------------------------------- #

# The box is only a coarse pre-filter (Haversine does the real cut), so pad
# it a little to guarantee it never clips a store that is genuinely inside
# the radius because of float error at the edge.
_BOX_PAD_KM = 0.2

# A radius larger than this is almost certainly a mistake, not a query.
MAX_RADIUS_KM = 100.0


def _coord_decimal(value):
    return Decimal(str(value)).quantize(Decimal("0.000001"))


def set_location(store, latitude, longitude):
    """Set (or clear) a store's map pin. Caller commits.

    Both coordinates together or neither. ``None`` / ``None`` clears the
    pin. An online-only store cannot have one — see :func:`set_online_only`.
    """
    lat, lng = validate_coords(latitude, longitude)

    if lat is None:
        store.latitude = None
        store.longitude = None
        return

    if store.is_online_only:
        raise CoordinateError("an online-only store has no map location")

    store.latitude = _coord_decimal(lat)
    store.longitude = _coord_decimal(lng)


def set_online_only(store, flag):
    """Toggle the online-only flag. Turning it on clears the map pin —
    an online seller has no shopfront to stand a customer in front of."""
    store.is_online_only = bool(flag)
    if store.is_online_only:
        store.latitude = None
        store.longitude = None


def nearby(lat, lng, radius_km, query=None):
    """Stores within ``radius_km`` of ``(lat, lng)``, nearest first.

    Two stages:

    1. A SQL bounding box — ``latitude BETWEEN … AND longitude BETWEEN …``
       — so the ``(latitude, longitude)`` index does the heavy filtering.
       The east–west half-width is scaled by ``cos(latitude)``: one degree
       of longitude is ``111.045 km × cos(lat)``, not 111.045. Using the
       flat value makes the box too narrow east–west and silently drops
       results.
    2. Haversine in Python on the survivors, dropping anything past the
       true (circular) radius, sorted ascending by real distance.

    Stores with a NULL pin — including every online-only store — are
    excluded, never treated as if they sat at ``(0, 0)``. Returns
    ``[(store, distance_km_rounded_to_1dp), …]``.
    """
    if query is None:
        query = Store.query

    lat_delta = (radius_km + _BOX_PAD_KM) / KM_PER_DEG_LAT
    cos_lat = max(math.cos(math.radians(lat)), 1e-6)
    lng_delta = (radius_km + _BOX_PAD_KM) / (KM_PER_DEG_LAT * cos_lat)

    in_box = query.filter(
        Store.is_online_only.is_(False),
        Store.latitude.isnot(None),
        Store.longitude.isnot(None),
        Store.latitude.between(lat - lat_delta, lat + lat_delta),
        Store.longitude.between(lng - lng_delta, lng + lng_delta),
    ).all()

    within = []
    for store in in_box:
        distance = haversine_km(
            lat, lng, float(store.latitude), float(store.longitude)
        )
        if distance <= radius_km:
            within.append((store, distance))

    within.sort(key=lambda pair: pair[1])
    return [(store, round(distance, 1)) for store, distance in within]
