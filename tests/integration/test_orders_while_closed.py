"""Ordering from a store that is shut.

Being closed and refusing an order stopped being the same thing. A store
closed by its *schedule* can take orders for later when its vendor has
said so; a store closed by an active *override* refuses regardless,
because an override is the vendor saying something is wrong right now.
See docs/decisions/0025-orders-while-closed.md.

Both ``store_service`` now() seams are frozen in every time-sensitive
test — ``_now_local`` and ``_now_utc``. Patching only one lets the
override arithmetic disagree with the schedule arithmetic.
"""

from datetime import datetime, time, timedelta, timezone

import pytest

from app.extensions import db
from app.models.store_hours import StoreHours
from app.services import store_service
from app.services.order_service import OrderError, assert_store_accepts_orders

BEIRUT = store_service.BEIRUT

# A Tuesday, deliberately mid-week so weekday arithmetic has room either way.
TUESDAY = datetime(2026, 9, 8, tzinfo=BEIRUT)


def _freeze(monkeypatch, local):
    """Freeze both seams. See the module docstring."""
    if local.tzinfo is None:
        local = local.replace(tzinfo=BEIRUT)
    monkeypatch.setattr(store_service, "_now_local", lambda: local)
    monkeypatch.setattr(
        store_service, "_now_utc", lambda: local.astimezone(timezone.utc)
    )


def _hours(store, entries):
    """Replace the schedule with (day, opens, closes) tuples. Monday = 0."""
    StoreHours.query.filter_by(store_id=store.id).delete()
    for day, opens, closes in entries:
        db.session.add(
            StoreHours(
                store_id=store.id,
                day_of_week=day,
                opens_at=time(*opens),
                closes_at=time(*closes),
            )
        )
    db.session.commit()


def _at(day_offset, hour, minute=0):
    return TUESDAY + timedelta(days=day_offset, hours=hour, minutes=minute)


# --------------------------------------------------------------------------- #
# Enforcement — schedule vs override
# --------------------------------------------------------------------------- #

@pytest.fixture()
def shop(make_store):
    """Open Mon-Sat 09:00-18:00, so a 23:00 Tuesday is closed by schedule."""
    store = make_store(open_always=False)
    _hours(store, [(day, (9, 0), (18, 0)) for day in range(6)])
    return store


def test_closed_by_schedule_refuses_by_default(monkeypatch, shop):
    """Unchanged behaviour: the flag defaults to False."""
    _freeze(monkeypatch, _at(0, 23))

    assert shop.accepts_orders_when_closed is False

    with pytest.raises(OrderError) as raised:
        assert_store_accepts_orders(shop)

    assert raised.value.payload["code"] == "store_closed"
    assert raised.value.payload["reason"] == store_service.CLOSED_OUTSIDE_HOURS


def test_closed_by_schedule_accepts_when_the_flag_is_set(monkeypatch, shop):
    _freeze(monkeypatch, _at(0, 23))

    shop.accepts_orders_when_closed = True
    db.session.commit()

    assert_store_accepts_orders(shop)          # must not raise


def test_an_override_refuses_even_with_the_flag_set(monkeypatch, shop):
    """The distinction the feature turns on.

    An override is the vendor saying something is wrong *now*. Letting
    orders through it would make setting one pointless.
    """
    _freeze(monkeypatch, _at(0, 11))           # inside opening hours

    shop.accepts_orders_when_closed = True
    store_service.set_override(
        shop, "closed", "Power outage",
        until=(_at(0, 15)).isoformat(),
    )
    db.session.commit()

    open_now, reason = store_service.is_open_now(shop)
    assert open_now is False
    assert reason == store_service.CLOSED_OVERRIDE

    with pytest.raises(OrderError) as raised:
        assert_store_accepts_orders(shop)
    assert raised.value.payload["reason"] == store_service.CLOSED_OVERRIDE


def test_an_override_refuses_without_the_flag_too(monkeypatch, shop):
    _freeze(monkeypatch, _at(0, 11))

    store_service.set_override(
        shop, "closed", "Power outage", until=_at(0, 15).isoformat()
    )
    db.session.commit()

    with pytest.raises(OrderError):
        assert_store_accepts_orders(shop)


def test_an_open_store_is_unaffected(monkeypatch, shop):
    _freeze(monkeypatch, _at(0, 11))

    assert_store_accepts_orders(shop)          # flag off, still open

    shop.accepts_orders_when_closed = True
    db.session.commit()
    assert_store_accepts_orders(shop)


# --------------------------------------------------------------------------- #
# The same rule through the HTTP layer
# --------------------------------------------------------------------------- #

def test_cart_add_and_checkout_both_honour_the_flag(
    client, auth, customer, make_product, monkeypatch, shop
):
    product = make_product(store=shop, stock=5)
    _freeze(monkeypatch, _at(0, 23))

    refused = client.post(
        "/api/cart/items",
        json={"product_id": product.id, "quantity": 1},
        headers=auth(customer),
    )
    assert refused.status_code == 400
    assert refused.get_json()["code"] == "store_closed"

    shop.accepts_orders_when_closed = True
    db.session.commit()

    added = client.post(
        "/api/cart/items",
        json={"product_id": product.id, "quantity": 1},
        headers=auth(customer),
    )
    assert added.status_code in (200, 201)

    placed = client.post(
        "/api/orders",
        json={
            "delivery_address": "1 Test Street",
            "delivery_city": "Beirut",
            "payment_method": "cash_on_delivery",
        },
        headers=auth(customer),
    )
    assert placed.status_code == 201, placed.get_json()


def test_checkout_is_refused_under_an_override_even_with_a_full_cart(
    client, auth, customer, make_product, monkeypatch, shop
):
    """The cart was filled while open; the override lands before checkout."""
    product = make_product(store=shop, stock=5)
    shop.accepts_orders_when_closed = True
    db.session.commit()

    _freeze(monkeypatch, _at(0, 11))
    assert client.post(
        "/api/cart/items",
        json={"product_id": product.id, "quantity": 1},
        headers=auth(customer),
    ).status_code in (200, 201)

    store_service.set_override(
        shop, "closed", "Burst pipe", until=_at(0, 16).isoformat()
    )
    db.session.commit()

    refused = client.post(
        "/api/orders",
        json={
            "delivery_address": "1 Test Street",
            "delivery_city": "Beirut",
            "payment_method": "cash_on_delivery",
        },
        headers=auth(customer),
    )
    assert refused.status_code == 400
    assert refused.get_json()["reason"] == store_service.CLOSED_OVERRIDE


def test_the_storefront_reports_the_flag(client, shop):
    shop.accepts_orders_when_closed = True
    db.session.commit()

    body = client.get(f"/api/stores/{shop.id}").get_json()
    store = body.get("store", body)
    assert store["accepts_orders_when_closed"] is True


# --------------------------------------------------------------------------- #
# next_opening_time
# --------------------------------------------------------------------------- #

def test_next_opening_is_none_without_any_hours(make_store, monkeypatch):
    store = make_store(open_always=False)
    StoreHours.query.filter_by(store_id=store.id).delete()
    db.session.commit()

    _freeze(monkeypatch, _at(0, 12))
    assert store_service.next_opening_time(store) is None


def test_next_opening_later_the_same_day(monkeypatch, shop):
    _freeze(monkeypatch, _at(0, 7))            # Tuesday 07:00, opens 09:00

    assert store_service.next_opening_time(shop) == _at(0, 9)


def test_next_opening_rolls_to_tomorrow_after_closing(monkeypatch, shop):
    _freeze(monkeypatch, _at(0, 23))           # Tuesday 23:00

    assert store_service.next_opening_time(shop) == _at(1, 9)


def test_next_opening_returns_now_while_open(monkeypatch, shop):
    """Already inside an interval — the next moment it is open is this one."""
    now = _at(0, 11)
    _freeze(monkeypatch, now)

    assert store_service.next_opening_time(shop) == now


def test_next_opening_across_a_split_day(monkeypatch, make_store):
    """09:00-14:00 and 16:00-20:00: the gap reopens at 16:00, not tomorrow."""
    store = make_store(open_always=False)
    _hours(store, [
        (day, opens, closes)
        for day in range(7)
        for opens, closes in (((9, 0), (14, 0)), ((16, 0), (20, 0)))
    ])

    _freeze(monkeypatch, _at(0, 15))           # in the afternoon gap
    assert store_service.next_opening_time(store) == _at(0, 16)

    _freeze(monkeypatch, _at(0, 21))           # after the second interval
    assert store_service.next_opening_time(store) == _at(1, 9)


def test_next_opening_with_an_interval_crossing_midnight(
    monkeypatch, make_store
):
    """20:00-02:00 every day. 01:00 is still inside last night's interval."""
    store = make_store(open_always=False)
    _hours(store, [(day, (20, 0), (2, 0)) for day in range(7)])

    # 01:00 Wednesday — the morning half of Tuesday's interval.
    _freeze(monkeypatch, _at(1, 1))
    assert store_service.next_opening_time(store) == _at(1, 1)

    # 10:00 Wednesday — shut, and the next opening is that evening.
    _freeze(monkeypatch, _at(1, 10))
    assert store_service.next_opening_time(store) == _at(1, 20)


def test_next_opening_skips_a_closed_sunday(monkeypatch, make_store):
    """Open Mon-Sat. On Sunday the answer is Monday, not later that day."""
    store = make_store(open_always=False)
    _hours(store, [(day, (9, 0), (18, 0)) for day in range(6)])

    sunday = TUESDAY + timedelta(days=5)       # 13 Sep 2026 is a Sunday
    assert sunday.weekday() == 6

    _freeze(monkeypatch, sunday.replace(hour=12))
    assert store_service.next_opening_time(store) == (
        sunday + timedelta(days=1)
    ).replace(hour=9)


def test_an_override_expiring_mid_closure_does_not_pull_the_opening_in(
    monkeypatch, shop
):
    """Override ends at 03:00, before the store would open anyway.

    The later of the two constraints is the schedule, so 09:00 stands.
    """
    _freeze(monkeypatch, _at(0, 22))

    store_service.set_override(
        shop, "closed", "Stocktake", until=_at(1, 3).isoformat()
    )
    db.session.commit()

    assert store_service.next_opening_time(shop) == _at(1, 9)


def test_an_override_expiring_mid_opening_pushes_the_opening_out(
    monkeypatch, shop
):
    """Override ends at 14:00 on a day scheduled 09:00-18:00.

    The store is shut until the override lifts, so it opens at 14:00 —
    the later of the two constraints, which is the whole point.
    """
    _freeze(monkeypatch, _at(0, 8))

    store_service.set_override(
        shop, "closed", "Deep clean", until=_at(0, 14).isoformat()
    )
    db.session.commit()

    assert store_service.next_opening_time(shop) == _at(0, 14)


def test_an_override_outlasting_the_day_opens_the_following_morning(
    monkeypatch, shop
):
    """Override ends at 20:00, after closing. Next opening is tomorrow."""
    _freeze(monkeypatch, _at(0, 10))

    store_service.set_override(
        shop, "closed", "Inventory", until=_at(0, 20).isoformat()
    )
    db.session.commit()

    assert store_service.next_opening_time(shop) == _at(1, 9)


def test_next_opening_stays_within_seven_days(monkeypatch, make_store):
    """A single weekly opening is still found; nothing runs away."""
    store = make_store(open_always=False)
    _hours(store, [(2, (9, 0), (17, 0))])      # Wednesdays only

    _freeze(monkeypatch, _at(0, 12))           # Tuesday
    opening = store_service.next_opening_time(store)

    assert opening == _at(1, 9)
    assert opening - _at(0, 12) <= timedelta(days=7)


def test_next_opening_across_the_spring_dst_change(monkeypatch, make_store):
    """Beirut moves to EEST overnight on 29 March 2026 (+02:00 -> +03:00).

    The answer is a wall-clock 09:00 on the far side, not 08:00 or 10:00 —
    the schedule is local wall time and ZoneInfo resolves the offset for
    the date in question (ADR 0013).
    """
    store = make_store(open_always=False)
    _hours(store, [(day, (9, 0), (18, 0)) for day in range(7)])

    saturday_night = datetime(2026, 3, 28, 22, 0, tzinfo=BEIRUT)
    _freeze(monkeypatch, saturday_night)

    opening = store_service.next_opening_time(store)

    assert opening == datetime(2026, 3, 29, 9, 0, tzinfo=BEIRUT)
    assert opening.hour == 9, "wall clock, not shifted by the transition"
    assert opening.utcoffset() == timedelta(hours=3), "EEST on that date"


def test_next_opening_across_the_autumn_dst_change(monkeypatch, make_store):
    """And back again on 25 October (+03:00 -> +02:00)."""
    store = make_store(open_always=False)
    _hours(store, [(day, (9, 0), (18, 0)) for day in range(7)])

    _freeze(monkeypatch, datetime(2026, 10, 24, 22, 0, tzinfo=BEIRUT))

    opening = store_service.next_opening_time(store)

    assert opening == datetime(2026, 10, 25, 9, 0, tzinfo=BEIRUT)
    assert opening.utcoffset() == timedelta(hours=2), "EET on that date"
