"""Store working hours + manual open/closed override (C.1).

Time is frozen explicitly everywhere — either by passing ``at`` straight to
``store_service.is_open_now`` or by monkeypatching ``store_service._now_local``
for the paths that don't take a moment (cart add, checkout). Nothing here
depends on when the suite runs.

Reference day: 2026-01-05 is a Monday, so ``weekday() == 0``. Beirut is on
EET (UTC+2) in January.
"""

import contextlib
from datetime import datetime, time, timedelta, timezone
from zoneinfo import ZoneInfo

from sqlalchemy import event

from app.extensions import db
from app.models.store_hours import StoreHours
from app.services import store_service

BEIRUT = ZoneInfo("Asia/Beirut")

MON, TUE, WED = 0, 1, 2


def beirut(year, month, day, hour, minute=0):
    return datetime(year, month, day, hour, minute, tzinfo=BEIRUT)


@contextlib.contextmanager
def count_queries():
    """Count SQL statements issued on db.engine for the duration of the block."""
    counter = {"n": 0}

    def _on_execute(conn, cursor, statement, parameters, context, executemany):
        counter["n"] += 1

    event.listen(db.engine, "before_cursor_execute", _on_execute)
    try:
        yield counter
    finally:
        event.remove(db.engine, "before_cursor_execute", _on_execute)


def add_hours(store, *rows):
    """rows: (day_of_week, "HH:MM", "HH:MM")"""
    for day, opens, closes in rows:
        db.session.add(
            StoreHours(
                store_id=store.id,
                day_of_week=day,
                opens_at=time.fromisoformat(opens),
                closes_at=time.fromisoformat(closes),
            )
        )
    db.session.commit()


# --------------------------------------------------------------------------- #
# is_open_now — schedule
# --------------------------------------------------------------------------- #

def test_open_inside_a_range(make_store):
    store = make_store(open_always=False)
    add_hours(store, (MON, "09:00", "17:00"))

    is_open, reason = store_service.is_open_now(store, at=beirut(2026, 1, 5, 10))

    assert is_open is True
    assert reason == store_service.OPEN_SCHEDULED


def test_closed_outside_a_range(make_store):
    store = make_store(open_always=False)
    add_hours(store, (MON, "09:00", "17:00"))

    is_open, reason = store_service.is_open_now(store, at=beirut(2026, 1, 5, 18))

    assert is_open is False
    assert reason == store_service.CLOSED_OUTSIDE_HOURS


def test_closes_at_boundary_is_closed(make_store):
    store = make_store(open_always=False)
    add_hours(store, (MON, "09:00", "17:00"))

    # 17:00 exactly — the interval is [09:00, 17:00).
    is_open, _ = store_service.is_open_now(store, at=beirut(2026, 1, 5, 17))
    assert is_open is False


def test_day_with_no_rows_is_closed(make_store):
    store = make_store(open_always=False)
    add_hours(store, (MON, "09:00", "17:00"))  # Monday only

    # Tuesday, well within Monday's window-of-day.
    is_open, reason = store_service.is_open_now(
        store, at=beirut(2026, 1, 6, 12)
    )
    assert is_open is False
    assert reason == store_service.CLOSED_OUTSIDE_HOURS


def test_range_crossing_midnight_is_open_at_0100_next_day(make_store):
    store = make_store(open_always=False)
    add_hours(store, (MON, "20:00", "02:00"))  # Mon 20:00 -> Tue 02:00

    # Tuesday 01:00 — belongs to Monday's interval.
    is_open, _ = store_service.is_open_now(store, at=beirut(2026, 1, 6, 1))
    assert is_open is True

    # Tuesday 03:00 — after it closed, and Tuesday has no row.
    is_open, _ = store_service.is_open_now(store, at=beirut(2026, 1, 6, 3))
    assert is_open is False

    # Monday 21:00 — the evening half of the same interval.
    is_open, _ = store_service.is_open_now(store, at=beirut(2026, 1, 5, 21))
    assert is_open is True


def test_two_ranges_one_day_closed_in_the_gap(make_store):
    store = make_store(open_always=False)
    add_hours(store, (WED, "09:00", "12:00"), (WED, "14:00", "18:00"))

    # 2026-01-07 is a Wednesday.
    assert store_service.is_open_now(store, at=beirut(2026, 1, 7, 10))[0] is True
    assert store_service.is_open_now(store, at=beirut(2026, 1, 7, 13))[0] is False
    assert store_service.is_open_now(store, at=beirut(2026, 1, 7, 15))[0] is True


def test_invisible_store_is_never_open(make_store):
    store = make_store(open_always=False, is_active=False)
    add_hours(store, (MON, "00:00", "23:59"))

    is_open, reason = store_service.is_open_now(store, at=beirut(2026, 1, 5, 12))
    assert is_open is False
    assert reason == store_service.CLOSED_NOT_VISIBLE


# --------------------------------------------------------------------------- #
# is_open_now — override
# --------------------------------------------------------------------------- #

def test_active_override_beats_the_schedule_both_ways(make_store):
    store = make_store(open_always=False)
    add_hours(store, (MON, "09:00", "17:00"))

    inside = beirut(2026, 1, 5, 10)
    outside = beirut(2026, 1, 5, 20)
    later_utc = (
        outside.astimezone(timezone.utc).replace(tzinfo=None)
        + timedelta(hours=2)
    )

    # Override CLOSED while the schedule says open.
    store.override_status = "closed"
    store.override_until = later_utc
    db.session.commit()
    is_open, reason = store_service.is_open_now(store, at=inside)
    assert is_open is False
    assert reason == store_service.CLOSED_OVERRIDE

    # Override OPEN while the schedule says closed.
    store.override_status = "open"
    db.session.commit()
    is_open, reason = store_service.is_open_now(store, at=outside)
    assert is_open is True
    assert reason == store_service.OPEN_OVERRIDE


def test_expired_override_is_ignored_and_not_mutated(make_store):
    store = make_store(open_always=False)
    add_hours(store, (MON, "09:00", "17:00"))

    now = beirut(2026, 1, 5, 10)
    store.override_status = "closed"
    # expired an hour ago
    store.override_until = (
        now.astimezone(timezone.utc).replace(tzinfo=None) - timedelta(hours=1)
    )
    db.session.commit()

    is_open, reason = store_service.is_open_now(store, at=now)

    assert is_open is True                     # fell through to the schedule
    assert reason == store_service.OPEN_SCHEDULED
    assert store.override_status == "closed"   # row untouched on read


# --------------------------------------------------------------------------- #
# Enforcement — cart add and checkout
# --------------------------------------------------------------------------- #

def test_adding_to_cart_from_a_closed_store_is_rejected(
    client, auth, customer, make_store, make_product, monkeypatch
):
    store = make_store(open_always=False)
    add_hours(store, (MON, "09:00", "17:00"))
    product = make_product(store=store, stock=5)

    # Freeze "now" to Monday 20:00 — outside the window.
    monkeypatch.setattr(
        store_service, "_now_local", lambda: beirut(2026, 1, 5, 20)
    )

    resp = client.post(
        "/api/cart/items",
        json={"product_id": product.id, "quantity": 1},
        headers=auth(customer),
    )

    assert resp.status_code == 400
    body = resp.get_json()
    assert body["code"] == "store_closed"


def test_checkout_from_a_closed_store_is_rejected(
    client, auth, customer, add_to_cart, make_store, make_product, monkeypatch
):
    store = make_store(open_always=False)
    add_hours(store, (MON, "09:00", "17:00"))
    product = make_product(store=store, stock=5)

    # Add while open...
    monkeypatch.setattr(
        store_service, "_now_local", lambda: beirut(2026, 1, 5, 10)
    )
    assert add_to_cart(customer, product).status_code == 200

    # ...then the store closes before checkout.
    monkeypatch.setattr(
        store_service, "_now_local", lambda: beirut(2026, 1, 5, 20)
    )
    resp = client.post(
        "/api/orders/preview",
        json={"delivery_city": "Beirut"},
        headers=auth(customer),
    )
    assert resp.status_code == 400
    assert resp.get_json()["code"] == "store_closed"


# --------------------------------------------------------------------------- #
# API — hours
# --------------------------------------------------------------------------- #

def test_get_and_put_hours_round_trip(client, auth, make_store):
    store = make_store(open_always=False)
    owner = store.owner

    put = client.put(
        f"/api/stores/{store.id}/hours",
        json={
            "hours": [
                {"day_of_week": 0, "opens_at": "09:00", "closes_at": "17:00"},
                {"day_of_week": 0, "opens_at": "18:00", "closes_at": "21:00"},
                {"day_of_week": 5, "opens_at": "10:00", "closes_at": "14:00"},
            ]
        },
        headers=auth(owner),
    )
    assert put.status_code == 200

    got = client.get(f"/api/stores/{store.id}/hours").get_json()["hours"]
    assert [(h["day_of_week"], h["opens_at"], h["closes_at"]) for h in got] == [
        (0, "09:00", "17:00"),
        (0, "18:00", "21:00"),
        (5, "10:00", "14:00"),
    ]

    # PUT replaces — an empty list clears the week.
    client.put(
        f"/api/stores/{store.id}/hours", json={"hours": []}, headers=auth(owner)
    )
    assert client.get(f"/api/stores/{store.id}/hours").get_json()["hours"] == []


def test_put_hours_rejects_overlapping_ranges(client, auth, make_store):
    store = make_store(open_always=False)

    resp = client.put(
        f"/api/stores/{store.id}/hours",
        json={
            "hours": [
                {"day_of_week": 2, "opens_at": "09:00", "closes_at": "13:00"},
                {"day_of_week": 2, "opens_at": "12:00", "closes_at": "15:00"},
            ]
        },
        headers=auth(store.owner),
    )

    assert resp.status_code == 400
    assert "overlap" in resp.get_json()["message"].lower()


def test_put_hours_rejects_a_bad_day_or_time(client, auth, make_store):
    store = make_store(open_always=False)

    bad_day = client.put(
        f"/api/stores/{store.id}/hours",
        json={"hours": [
            {"day_of_week": 7, "opens_at": "09:00", "closes_at": "17:00"}
        ]},
        headers=auth(store.owner),
    )
    assert bad_day.status_code == 400

    bad_time = client.put(
        f"/api/stores/{store.id}/hours",
        json={"hours": [
            {"day_of_week": 1, "opens_at": "9am", "closes_at": "17:00"}
        ]},
        headers=auth(store.owner),
    )
    assert bad_time.status_code == 400


def test_touching_ranges_are_allowed(client, auth, make_store):
    store = make_store(open_always=False)
    resp = client.put(
        f"/api/stores/{store.id}/hours",
        json={"hours": [
            {"day_of_week": 3, "opens_at": "09:00", "closes_at": "12:00"},
            {"day_of_week": 3, "opens_at": "12:00", "closes_at": "17:00"},
        ]},
        headers=auth(store.owner),
    )
    assert resp.status_code == 200


def test_non_owner_cannot_set_hours(
    client, auth, make_store, make_user
):
    store = make_store(open_always=False)
    intruder = make_user("vendor", email="intruder-hours@test.local")

    resp = client.put(
        f"/api/stores/{store.id}/hours",
        json={"hours": []},
        headers=auth(intruder),
    )
    assert resp.status_code == 403


def test_customer_cannot_set_hours(client, auth, make_store, customer):
    store = make_store(open_always=False)
    resp = client.put(
        f"/api/stores/{store.id}/hours",
        json={"hours": []},
        headers=auth(customer),
    )
    assert resp.status_code == 403


# --------------------------------------------------------------------------- #
# API — override
# --------------------------------------------------------------------------- #

def _future(hours):
    return (
        datetime.now(timezone.utc).replace(microsecond=0)
        + timedelta(hours=hours)
    ).isoformat()


def test_set_and_clear_override(client, auth, make_store):
    store = make_store(open_always=False)

    patched = client.patch(
        f"/api/stores/{store.id}/override",
        json={
            "status": "closed",
            "reason": "Power outage",
            "until": _future(6),
        },
        headers=auth(store.owner),
    )
    assert patched.status_code == 200
    payload = patched.get_json()["store"]
    assert payload["override_status"] == "closed"
    assert payload["override_reason"] == "Power outage"
    assert payload["override_until"].endswith("+00:00")

    cleared = client.delete(
        f"/api/stores/{store.id}/override", headers=auth(store.owner)
    )
    assert cleared.status_code == 200
    assert cleared.get_json()["store"]["override_status"] is None


def test_override_rejects_missing_past_and_far_future_until(
    client, auth, make_store
):
    store = make_store(open_always=False)
    url = f"/api/stores/{store.id}/override"
    headers = auth(store.owner)

    assert client.patch(
        url, json={"status": "closed"}, headers=headers
    ).status_code == 400

    past = (
        datetime.now(timezone.utc) - timedelta(hours=1)
    ).isoformat()
    assert client.patch(
        url, json={"status": "closed", "until": past}, headers=headers
    ).status_code == 400

    too_far = (
        datetime.now(timezone.utc) + timedelta(days=8)
    ).isoformat()
    assert client.patch(
        url, json={"status": "closed", "until": too_far}, headers=headers
    ).status_code == 400


def test_override_rejects_a_bad_status(client, auth, make_store):
    store = make_store(open_always=False)
    resp = client.patch(
        f"/api/stores/{store.id}/override",
        json={"status": "maybe", "until": _future(3)},
        headers=auth(store.owner),
    )
    assert resp.status_code == 400


def test_non_owner_cannot_set_override(client, auth, make_store, make_user):
    store = make_store(open_always=False)
    intruder = make_user("vendor", email="intruder-ovr@test.local")

    resp = client.patch(
        f"/api/stores/{store.id}/override",
        json={"status": "closed", "until": _future(3)},
        headers=auth(intruder),
    )
    assert resp.status_code == 403


# --------------------------------------------------------------------------- #
# API — override duration presets (resolved server-side, ADR 0013)
# --------------------------------------------------------------------------- #

def _freeze_now(monkeypatch, at):
    """Pin both time seams to one instant (given as any aware datetime)."""
    monkeypatch.setattr(
        store_service, "_now_local", lambda: at.astimezone(BEIRUT)
    )
    monkeypatch.setattr(
        store_service, "_now_utc", lambda: at.astimezone(timezone.utc)
    )


def _set_override(client, auth, store, body):
    return client.patch(
        f"/api/stores/{store.id}/override",
        json={"status": "closed", **body},
        headers=auth(store.owner),
    )


def test_named_duration_end_of_day_is_2359_on_the_beirut_date(
    client, auth, make_store, monkeypatch
):
    """The client sends only the name; the server resolves it in Beirut.

    Here "now" is 04:00 on 2026-01-06 Beirut — for a caller whose own clock
    still reads the 5th in a western zone, "end of day" must be the 6th's
    23:59 in Beirut, not the caller's date and not the caller's midnight.
    """
    store = make_store(open_always=False)
    _freeze_now(monkeypatch, datetime(2026, 1, 6, 4, 0, tzinfo=BEIRUT))

    resp = _set_override(client, auth, store, {"duration": "end_of_day"})

    assert resp.status_code == 200
    # 23:59 Beirut on 2026-01-06 (EET, +2) == 21:59 UTC.
    assert resp.get_json()["store"]["override_until"] == (
        "2026-01-06T21:59:00+00:00"
    )


def test_named_duration_end_of_day_honours_summer_dst(
    client, auth, make_store, monkeypatch
):
    store = make_store(open_always=False)
    _freeze_now(monkeypatch, datetime(2026, 7, 1, 12, 0, tzinfo=BEIRUT))

    resp = _set_override(client, auth, store, {"duration": "end_of_day"})

    assert resp.status_code == 200
    # 23:59 Beirut on 2026-07-01 (EEST, +3) == 20:59 UTC — an hour earlier
    # than the winter case, which a fixed offset would get wrong.
    assert resp.get_json()["store"]["override_until"] == (
        "2026-07-01T20:59:00+00:00"
    )


def test_named_duration_tomorrow_morning_is_0800_beirut_next_day(
    client, auth, make_store, monkeypatch
):
    store = make_store(open_always=False)
    _freeze_now(monkeypatch, datetime(2026, 1, 5, 22, 30, tzinfo=BEIRUT))

    resp = _set_override(client, auth, store, {"duration": "tomorrow_morning"})

    assert resp.status_code == 200
    # 08:00 Beirut on 2026-01-06 (EET, +2) == 06:00 UTC.
    assert resp.get_json()["store"]["override_until"] == (
        "2026-01-06T06:00:00+00:00"
    )


def test_named_duration_relative_offsets(
    client, auth, make_store, monkeypatch
):
    store = make_store(open_always=False)
    _freeze_now(monkeypatch, datetime(2026, 1, 5, 10, 0, tzinfo=timezone.utc))

    one = _set_override(client, auth, store, {"duration": "1h"})
    assert one.status_code == 200
    assert one.get_json()["store"]["override_until"] == (
        "2026-01-05T11:00:00+00:00"
    )

    three = _set_override(client, auth, store, {"duration": "3h"})
    assert three.status_code == 200
    assert three.get_json()["store"]["override_until"] == (
        "2026-01-05T13:00:00+00:00"
    )


def test_custom_duration_still_takes_an_explicit_instant(
    client, auth, make_store
):
    store = make_store(open_always=False)

    ok = _set_override(
        client, auth, store, {"duration": "custom", "until": _future(5)}
    )
    assert ok.status_code == 200

    missing = _set_override(client, auth, store, {"duration": "custom"})
    assert missing.status_code == 400


def test_unknown_duration_is_rejected(client, auth, make_store):
    store = make_store(open_always=False)
    resp = _set_override(client, auth, store, {"duration": "next_week"})
    assert resp.status_code == 400


# --------------------------------------------------------------------------- #
# API — payload flags
# --------------------------------------------------------------------------- #

def test_store_payload_carries_open_and_override_fields(
    client, auth, make_store, monkeypatch
):
    store = make_store(open_always=False)
    add_hours(store, (MON, "09:00", "17:00"))

    monkeypatch.setattr(
        store_service, "_now_local", lambda: beirut(2026, 1, 5, 10)
    )

    detail = client.get(f"/api/stores/{store.id}").get_json()["store"]
    assert detail["is_open_now"] is True
    assert "override_status" in detail
    assert "override_reason" in detail
    assert "override_until" in detail

    listing = client.get("/api/stores").get_json()["stores"]
    row = next(s for s in listing if s["id"] == store.id)
    assert row["is_open_now"] is True


def test_store_directory_does_not_issue_a_query_per_store(client, make_store):
    """The directory's query count must not grow with the number of stores.

    _store_with_status() calls is_open_now() for every row, which walks
    store.hours. Without selectinload(Store.hours) that is one extra SELECT
    per store — a classic N+1 (CL-18).
    """
    for _ in range(3):
        make_store()  # make_store gives each a full 7-row week

    with count_queries() as first:
        assert client.get("/api/stores?limit=10").status_code == 200

    for _ in range(7):
        make_store()  # 10 stores now — still a single page

    with count_queries() as second:
        assert client.get("/api/stores?limit=10").status_code == 200

    assert second["n"] == first["n"]
