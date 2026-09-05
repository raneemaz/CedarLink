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
import re
from datetime import datetime, timedelta, timezone
from decimal import Decimal
from urllib.parse import urlsplit, urlunsplit
from zoneinfo import ZoneInfo

from app.extensions import db
from app.models.store import Store
from app.models.store_hours import StoreHours
from app.models.store_social_link import (
    EMAIL,
    FACEBOOK,
    INSTAGRAM,
    PHONE,
    PLATFORMS,
    StoreSocialLink,
    TIKTOK,
    WEBSITE,
    WHATSAPP,
)
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


# --------------------------------------------------------------------------- #
# Social and contact links
#
# The value stored is the finished href. It is built here, out of the
# vendor's input, rather than being the vendor's input — because it ends up
# in an anchor on a public page, and a vendor-supplied string in an href is
# stored cross-site scripting against every customer who clicks it. That is
# also why the scheme check lives in this module and not in the vendor form:
# a form check is bypassed by calling PUT /api/stores/<id>/social-links
# directly.
# --------------------------------------------------------------------------- #

class SocialLinkError(ValueError):
    """Invalid social/contact input — the route returns it as 400."""


# The only schemes a vendor may hand us. mailto: and tel: are never
# accepted as input; they are constructed below for the email and phone
# fields, whose values are validated as an address and a number first.
ALLOWED_INPUT_SCHEMES = ("http", "https")

# Everything the column may ever hold, checked once at the end as a
# backstop: if a future edit to this module lets something else through,
# it fails here rather than on a customer's browser.
_ALLOWED_VALUE_PREFIXES = ("https://", "http://", "mailto:", "tel:")

# platform -> (canonical prefix, hosts accepted in a pasted URL)
_PROFILE_PLATFORMS = {
    INSTAGRAM: (
        "https://www.instagram.com/",
        ("instagram.com", "www.instagram.com"),
    ),
    FACEBOOK: (
        "https://www.facebook.com/",
        ("facebook.com", "www.facebook.com", "m.facebook.com", "fb.com"),
    ),
    TIKTOK: (
        "https://www.tiktok.com/@",
        ("tiktok.com", "www.tiktok.com"),
    ),
}

# What the three profile platforms allow in a handle. Deliberately narrower
# than any of them documents: everything outside this set is far more likely
# to be a paste accident than a real account name.
_HANDLE_RE = re.compile(r"^[A-Za-z0-9._-]{1,60}$")

# Not RFC 5322 — that grammar accepts addresses no mail server will. This is
# the shape a person actually types, and it is the shape the browser's own
# type="email" check applies.
_EMAIL_RE = re.compile(r"^[^@\s]+@[^@\s.]+(\.[^@\s.]+)+$")

_MAX_VALUE_LENGTH = 500

# 7 is the shortest national number in use anywhere; 15 is the E.164 ceiling.
_MIN_PHONE_DIGITS = 7
_MAX_PHONE_DIGITS = 15


def _clean_input(raw):
    """Trim, and refuse anything with a control character in it.

    Browsers strip tabs, newlines and NULs out of a URL before resolving the
    scheme, so ``java\tscript:alert(1)`` navigates as ``javascript:``. The
    scheme check below would not see it. Rejecting the characters outright
    is simpler than trying to match the parser.
    """
    if not isinstance(raw, str):
        raise SocialLinkError("Each link value must be text")

    value = raw.strip()

    if any(ord(ch) < 0x20 or ord(ch) == 0x7F for ch in value):
        raise SocialLinkError("A link may not contain control characters")

    if len(value) > _MAX_VALUE_LENGTH:
        raise SocialLinkError(
            f"A link may be at most {_MAX_VALUE_LENGTH} characters"
        )

    return value


def _scheme_of(value):
    """The scheme a browser would resolve, lowercased, or ``None``."""
    match = re.match(r"^([A-Za-z][A-Za-z0-9+.-]*):", value)
    return match.group(1).lower() if match else None


def _assert_safe_scheme(value):
    """Reject javascript:, data:, file: and every other non-web scheme."""
    scheme = _scheme_of(value)

    if scheme is not None and scheme not in ALLOWED_INPUT_SCHEMES:
        raise SocialLinkError(
            f"'{scheme}:' links are not allowed — use http or https"
        )


def _strip_known_host(value, hosts):
    """``instagram.com/name`` -> ``name``. Returns ``None`` if no host matched."""
    lowered = value.lower()

    for host in hosts:
        for candidate in (host + "/", host):
            if lowered.startswith(candidate):
                return value[len(candidate):]

    return None


def _normalize_profile(platform, value):
    """A handle, @handle, host/handle or full URL -> the canonical profile URL."""
    prefix, hosts = _PROFILE_PLATFORMS[platform]

    _assert_safe_scheme(value)

    handle = None

    if _scheme_of(value) is not None:
        parts = urlsplit(value)

        if parts.hostname is None or parts.hostname.lower() not in hosts:
            raise SocialLinkError(
                f"That is not a {platform} address"
            )

        handle = parts.path

        # A pasted profile URL routinely carries ?igshid=... or a tracking
        # fragment. Neither identifies the account, so neither is stored.
        if parts.query or parts.fragment:
            handle = handle or ""
    else:
        stripped = _strip_known_host(value, hosts)
        handle = value if stripped is None else stripped

    handle = handle.strip().strip("/")
    handle = handle.split("?", 1)[0].split("#", 1)[0]
    handle = handle.lstrip("@")

    if not handle:
        raise SocialLinkError(f"A {platform} handle is required")

    if not _HANDLE_RE.match(handle):
        raise SocialLinkError(
            f"'{handle}' is not a valid {platform} handle"
        )

    return prefix + handle


def _digits_of(value):
    return "".join(ch for ch in value if ch.isdigit())


def _international_digits(value, field):
    """A typed phone number as bare international digits.

    Accepts ``+961 3 100 001``, ``00961-3-100-001`` and ``9613100001``. A
    number that still starts with a trunk ``0`` after that is a national
    format we cannot expand without guessing the country, so it is refused
    with an explanation rather than stored as something undialable.
    """
    _assert_safe_scheme(value)

    if not re.match(r"^\+?[0-9 ()./-]+$", value):
        raise SocialLinkError(f"'{value}' is not a valid {field} number")

    digits = _digits_of(value)

    if digits.startswith("00"):
        digits = digits[2:]

    if digits.startswith("0"):
        raise SocialLinkError(
            "Include the country code, for example +961 3 123 456"
        )

    if not _MIN_PHONE_DIGITS <= len(digits) <= _MAX_PHONE_DIGITS:
        raise SocialLinkError(f"'{value}' is not a valid {field} number")

    return digits


def _normalize_website(value):
    """A bare domain or a full URL -> an https URL. No other scheme."""
    _assert_safe_scheme(value)

    if _scheme_of(value) is None:
        value = "https://" + value

    parts = urlsplit(value)

    if parts.scheme.lower() not in ALLOWED_INPUT_SCHEMES:
        raise SocialLinkError("A website must be an http or https address")

    # A hostname with no dot is a hostname on somebody's LAN, not a website.
    if not parts.hostname or "." not in parts.hostname.strip("."):
        raise SocialLinkError(f"'{value}' is not a valid website address")

    return urlunsplit(
        (
            parts.scheme.lower(),
            parts.netloc.lower(),
            parts.path or "/",
            parts.query,
            "",
        )
    )


def _normalize_email(value):
    """An address, with or without a mailto:, -> ``mailto:address``."""
    if value.lower().startswith("mailto:"):
        value = value[len("mailto:"):].strip()

    _assert_safe_scheme(value)

    if not _EMAIL_RE.match(value):
        raise SocialLinkError(f"'{value}' is not a valid email address")

    return "mailto:" + value


def _normalize_phone(value):
    """A typed number, with or without a tel:, -> ``tel:+digits``."""
    if value.lower().startswith("tel:"):
        value = value[len("tel:"):].strip()

    return "tel:+" + _international_digits(value, "phone")


def normalize_social_value(platform, raw):
    """The stored, ready-to-render value for one platform.

    Raises :class:`SocialLinkError` for an unknown platform, an empty value,
    a value that does not parse as that platform, or any scheme other than
    http/https.
    """
    if platform not in PLATFORMS:
        raise SocialLinkError(f"'{platform}' is not a supported platform")

    value = _clean_input(raw)

    if not value:
        raise SocialLinkError(f"A value is required for {platform}")

    if platform in _PROFILE_PLATFORMS:
        normalized = _normalize_profile(platform, value)
    elif platform == WHATSAPP:
        normalized = "https://wa.me/" + _international_digits(
            value, "WhatsApp"
        )
    elif platform == WEBSITE:
        normalized = _normalize_website(value)
    elif platform == EMAIL:
        normalized = _normalize_email(value)
    elif platform == PHONE:
        normalized = _normalize_phone(value)
    else:
        raise SocialLinkError(f"'{platform}' is not a supported platform")

    if not normalized.startswith(_ALLOWED_VALUE_PREFIXES):
        raise SocialLinkError("A link must be an http or https address")

    if len(normalized) > _MAX_VALUE_LENGTH:
        raise SocialLinkError(
            f"A link may be at most {_MAX_VALUE_LENGTH} characters"
        )

    return normalized


def parse_social_links(entries):
    """Validate and normalise a whole submitted set. Returns ``{platform: value}``.

    A platform that is absent, or present with a blank value, is not in the
    result — that is how the vendor form clears a field.
    """
    if entries is None:
        entries = []

    if not isinstance(entries, list):
        raise SocialLinkError("social_links must be a list")

    normalized = {}

    for entry in entries:
        if not isinstance(entry, dict):
            raise SocialLinkError("Each social link must be an object")

        platform = entry.get("platform")

        if platform not in PLATFORMS:
            raise SocialLinkError(
                f"'{platform}' is not a supported platform"
            )

        if platform in normalized:
            raise SocialLinkError(
                f"'{platform}' appears more than once — a store may have "
                f"one of each"
            )

        raw = entry.get("value")

        # Absent or blank clears the platform rather than storing an empty
        # row, so the form does not need a separate delete call per field.
        if raw is None or (isinstance(raw, str) and not raw.strip()):
            normalized[platform] = None
            continue

        normalized[platform] = normalize_social_value(platform, raw)

    return {
        platform: value
        for platform, value in normalized.items()
        if value is not None
    }


def replace_social_links(store, entries):
    """Replace the store's whole set of links, in the caller's transaction.

    Diffed by platform, never cleared and recreated. Within one flush
    SQLAlchemy emits INSERTs before DELETEs, so re-adding a platform the
    store already had would collide with the row that has not been deleted
    yet — a UNIQUE violation on (store_id, platform), which is exactly how
    ``set_interests`` used to fail. Keeping a link the vendor did not touch
    is also an UPDATE of nothing rather than a delete and an insert, so its
    ``created_at`` stays honest.
    """
    wanted = parse_social_links(entries)

    existing = {link.platform: link for link in store.social_links}

    for platform, value in wanted.items():
        link = existing.get(platform)

        if link is None:
            store.social_links.append(
                StoreSocialLink(platform=platform, value=value)
            )
        elif link.value != value:
            link.value = value

    # Disjoint from the loop above by construction, so nothing here depends
    # on flush ordering either.
    for platform, link in existing.items():
        if platform not in wanted:
            store.social_links.remove(link)
            db.session.delete(link)

    return wanted


def social_links_payload(store):
    """The store's links, in the order the interface shows them."""
    by_platform = {link.platform: link for link in store.social_links}

    return [
        by_platform[platform].to_dict()
        for platform in PLATFORMS
        if platform in by_platform
    ]
