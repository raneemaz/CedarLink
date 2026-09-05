"""Vendor dashboard analytics.

Two things here are not ordinary feature tests. The scoping test is a
security test: an analytics endpoint that forgets whose store it is
answering about discloses a competitor's takings. And the money tests pin
down three distinctions the figures would otherwise quietly blur —
revenue against delivery collected, goods against discounts, and money in
hand against money still owed.
"""

from datetime import date, datetime, time, timedelta, timezone
from decimal import Decimal
from zoneinfo import ZoneInfo

import pytest

from app.extensions import db as _db
from app.models.coupon import Coupon
from app.models.coupon_redemption import CouponRedemption
from app.models.order import Order
from app.models.order_item import OrderItem
from app.services import analytics_service

BEIRUT = ZoneInfo("Asia/Beirut")


# --------------------------------------------------------------------------- #
# A fixture with numbers we can add up by hand
# --------------------------------------------------------------------------- #

def _utc(day, hour=12, minute=0):
    """A Beirut wall-clock instant, stored the way orders store it."""
    return (
        datetime.combine(day, time(hour, minute), tzinfo=BEIRUT)
        .astimezone(timezone.utc)
        .replace(tzinfo=None)
    )


def _place(store, customer, lines, status="delivered", on=None,
           delivery_fee="0.00", discount=None, hour=12):
    """Write one order with exact money, at an exact Beirut day and hour.

    Written directly rather than through checkout: these tests are about
    what the aggregates make of stored orders, and checkout can only
    create orders now, at today's stock levels and today's prices.
    """
    goods = sum(
        Decimal(str(price)) * quantity for _, price, quantity in lines
    )
    discount_amount = Decimal(discount) if discount else Decimal("0.00")
    at = _utc(on or date.today(), hour)

    order = Order(
        user_id=customer.id,
        store_id=store.id,
        status=status,
        delivery_address="1 Test Street",
        delivery_city="Beirut",
        # The stored invariant the whole module reads back:
        # total = goods - discount + delivery.
        total_price=goods - discount_amount + Decimal(delivery_fee),
        delivery_fee=Decimal(delivery_fee),
        created_at=at,
        updated_at=at,
    )
    _db.session.add(order)
    _db.session.flush()

    for product, price, quantity in lines:
        _db.session.add(
            OrderItem(
                order_id=order.id,
                product_id=product.id,
                quantity=quantity,
                unit_price=Decimal(str(price)),
            )
        )

    if discount_amount:
        coupon = Coupon(
            code=f"TEST{order.id}",
            discount_type="fixed",
            value=discount_amount,
            store_id=store.id,
            is_active=True,
        )
        _db.session.add(coupon)
        _db.session.flush()
        _db.session.add(
            CouponRedemption(
                coupon_id=coupon.id,
                user_id=customer.id,
                order_id=order.id,
                amount_applied=discount_amount,
            )
        )

    _db.session.commit()
    return order


@pytest.fixture()
def shop(make_store, make_product, make_user):
    """A store, three products and a customer, with nothing sold yet."""
    store = make_store()

    return {
        "store": store,
        "owner": store.owner,
        "customer": make_user("customer"),
        # Cheap and popular vs dear and rare — so "most units" and "most
        # revenue" are genuinely different questions.
        "zaatar": make_product(store=store, price=3.50, stock=100),
        "oil": make_product(store=store, price=12.00, stock=100),
        "nuts": make_product(store=store, price=14.00, stock=100),
    }


def _get(client, auth, user, **params):
    query = "&".join(f"{k}={v}" for k, v in params.items())
    return client.get(
        f"/api/vendor/dashboard{'?' + query if query else ''}",
        headers=auth(user),
    )


TODAY = date(2026, 6, 15)
RANGE = {"from": "2026-06-01", "to": "2026-06-30"}


# --------------------------------------------------------------------------- #
# Totals against a known fixture
# --------------------------------------------------------------------------- #

def test_totals_are_right_against_a_fixture_we_can_add_up(
    client, auth, shop
):
    store, customer = shop["store"], shop["customer"]

    # 2 x 12.00 + 3 x 3.50 = 34.50 goods, 2.50 off, 3.00 delivery
    _place(store, customer,
           [(shop["oil"], 12.00, 2), (shop["zaatar"], 3.50, 3)],
           status="delivered", on=TODAY, delivery_fee="3.00",
           discount="2.50")
    # 1 x 14.00 = 14.00 goods, no coupon, 2.00 delivery
    _place(store, customer, [(shop["nuts"], 14.00, 1)],
           status="delivered", on=TODAY, delivery_fee="2.00")

    body = _get(client, auth, shop["owner"], **RANGE).get_json()

    collected = body["money"]["collected"]

    assert collected["orders"] == 2
    assert collected["units"] == 6
    assert collected["goods_sold"] == "48.50"
    assert collected["discounts"] == "2.50"
    assert collected["revenue"] == "46.00"
    assert collected["delivery"] == "5.00"

    assert body["totals"]["orders"] == 2
    assert body["totals"]["units_sold"] == 6
    # 46.00 revenue over 2 delivered orders.
    assert body["totals"]["average_order_value"] == "23.00"
    assert body["has_orders"] is True


def test_revenue_is_goods_minus_discount_and_matches_the_stored_totals(
    client, auth, shop
):
    """Cross-check against the other stored representation of the same
    money: total_price - delivery_fee must equal goods - discount."""
    store, customer = shop["store"], shop["customer"]

    _place(store, customer, [(shop["oil"], 12.00, 2)], status="delivered",
           on=TODAY, delivery_fee="3.00", discount="4.00")

    body = _get(client, auth, shop["owner"], **RANGE).get_json()

    stored = sum(
        (order.total_price - order.delivery_fee
         for order in Order.query.filter_by(store_id=store.id)),
        Decimal("0.00"),
    )

    assert body["money"]["collected"]["revenue"] == f"{stored:.2f}"
    assert body["money"]["collected"]["revenue"] == "20.00"


# --------------------------------------------------------------------------- #
# Delivery is a pass-through, never revenue
# --------------------------------------------------------------------------- #

def test_the_delivery_fee_is_reported_but_never_inside_revenue(
    client, auth, shop
):
    store, customer = shop["store"], shop["customer"]

    _place(store, customer, [(shop["oil"], 12.00, 1)], status="delivered",
           on=TODAY, delivery_fee="7.50")

    collected = _get(
        client, auth, shop["owner"], **RANGE
    ).get_json()["money"]["collected"]

    assert collected["goods_sold"] == "12.00"
    assert collected["revenue"] == "12.00"
    assert collected["delivery"] == "7.50"
    # The vendor's takings are the goods. The driver's money is separate
    # and is not in any figure the interface calls revenue.
    assert Decimal(collected["revenue"]) < Decimal("19.50")


def test_a_discount_reduces_revenue_and_is_reported_on_its_own(
    client, auth, shop
):
    store, customer = shop["store"], shop["customer"]

    _place(store, customer, [(shop["nuts"], 14.00, 2)], status="delivered",
           on=TODAY, discount="5.00", delivery_fee="1.00")

    collected = _get(
        client, auth, shop["owner"], **RANGE
    ).get_json()["money"]["collected"]

    assert collected["goods_sold"] == "28.00"
    assert collected["discounts"] == "5.00"
    assert collected["revenue"] == "23.00"


# --------------------------------------------------------------------------- #
# Collected vs in progress vs cancelled
# --------------------------------------------------------------------------- #

def test_delivered_is_collected_and_pending_processing_are_in_progress(
    client, auth, shop
):
    store, customer = shop["store"], shop["customer"]

    _place(store, customer, [(shop["oil"], 12.00, 1)], status="delivered",
           on=TODAY, delivery_fee="2.00")
    _place(store, customer, [(shop["nuts"], 14.00, 1)], status="processing",
           on=TODAY, delivery_fee="2.00")
    _place(store, customer, [(shop["zaatar"], 3.50, 2)], status="pending",
           on=TODAY, delivery_fee="2.00")

    money = _get(client, auth, shop["owner"], **RANGE).get_json()["money"]

    assert money["collected"]["orders"] == 1
    assert money["collected"]["revenue"] == "12.00"

    assert money["in_progress"]["orders"] == 2
    assert money["in_progress"]["revenue"] == "21.00"

    # Two separate figures. Nothing in the payload adds them together.
    assert money["collected"]["revenue"] != money["in_progress"]["revenue"]


def test_revenue_counts_delivered_orders_only(client, auth, shop):
    store, customer = shop["store"], shop["customer"]

    _place(store, customer, [(shop["oil"], 12.00, 5)], status="pending",
           on=TODAY)
    _place(store, customer, [(shop["oil"], 12.00, 5)], status="processing",
           on=TODAY)
    _place(store, customer, [(shop["oil"], 12.00, 5)], status="canceled",
           on=TODAY)
    _place(store, customer, [(shop["zaatar"], 3.50, 1)], status="delivered",
           on=TODAY)

    body = _get(client, auth, shop["owner"], **RANGE).get_json()

    assert body["money"]["collected"]["revenue"] == "3.50"


def test_a_cancelled_order_is_in_neither_money_bucket_but_is_counted(
    client, auth, shop
):
    store, customer = shop["store"], shop["customer"]

    _place(store, customer, [(shop["nuts"], 14.00, 3)], status="canceled",
           on=TODAY, delivery_fee="2.00")

    body = _get(client, auth, shop["owner"], **RANGE).get_json()

    assert body["money"]["collected"]["revenue"] == "0.00"
    assert body["money"]["in_progress"]["revenue"] == "0.00"
    assert body["money"]["collected"]["delivery"] == "0.00"
    assert body["money"]["in_progress"]["delivery"] == "0.00"

    # It still happened, and the vendor should see that it did.
    assert body["orders_by_status"]["canceled"] == 1
    assert body["totals"]["orders"] == 1
    # Cancelled goods came back, so they were never sold.
    assert body["totals"]["units_sold"] == 0


def test_an_order_cancelled_after_being_processed_leaves_in_progress(
    client, auth, shop
):
    """The case that breaks a naive "everything not delivered is coming":
    the order was in progress, and now it is nothing."""
    store, customer = shop["store"], shop["customer"]

    order = _place(store, customer, [(shop["oil"], 12.00, 2)],
                   status="processing", on=TODAY, delivery_fee="3.00")

    before = _get(client, auth, shop["owner"], **RANGE).get_json()
    assert before["money"]["in_progress"]["revenue"] == "24.00"
    assert before["orders_by_status"]["processing"] == 1

    order.status = "canceled"
    _db.session.commit()

    after = _get(client, auth, shop["owner"], **RANGE).get_json()

    assert after["money"]["in_progress"]["revenue"] == "0.00"
    assert after["money"]["in_progress"]["orders"] == 0
    assert after["money"]["collected"]["revenue"] == "0.00"
    assert after["orders_by_status"]["processing"] == 0
    assert after["orders_by_status"]["canceled"] == 1
    assert after["totals"]["orders"] == 1


# --------------------------------------------------------------------------- #
# The date range
# --------------------------------------------------------------------------- #

def test_the_range_includes_both_boundary_days_whole(client, auth, shop):
    store, customer = shop["store"], shop["customer"]

    start, end = date(2026, 6, 1), date(2026, 6, 30)

    # The first and last minute of the range, in Beirut local time.
    _place(store, customer, [(shop["zaatar"], 3.50, 1)], status="delivered",
           on=start, hour=0)
    _place(store, customer, [(shop["zaatar"], 3.50, 1)], status="delivered",
           on=end, hour=23)

    body = _get(client, auth, shop["owner"],
                **{"from": start.isoformat(), "to": end.isoformat()}
                ).get_json()

    assert body["totals"]["orders"] == 2
    assert body["money"]["collected"]["revenue"] == "7.00"


def test_the_range_excludes_the_days_just_outside_it(client, auth, shop):
    store, customer = shop["store"], shop["customer"]

    start, end = date(2026, 6, 1), date(2026, 6, 30)

    _place(store, customer, [(shop["oil"], 12.00, 1)], status="delivered",
           on=start - timedelta(days=1), hour=23)
    _place(store, customer, [(shop["oil"], 12.00, 1)], status="delivered",
           on=end + timedelta(days=1), hour=0)
    _place(store, customer, [(shop["zaatar"], 3.50, 1)], status="delivered",
           on=date(2026, 6, 15))

    body = _get(client, auth, shop["owner"],
                **{"from": start.isoformat(), "to": end.isoformat()}
                ).get_json()

    assert body["totals"]["orders"] == 1
    assert body["money"]["collected"]["revenue"] == "3.50"


def test_the_default_range_is_the_last_thirty_days(client, auth, shop):
    body = _get(client, auth, shop["owner"]).get_json()

    assert body["range"]["days"] == 30
    assert len(body["orders_per_day"]) == 30

    start, end = analytics_service.resolve_range()
    assert body["range"]["from"] == start.isoformat()
    assert body["range"]["to"] == end.isoformat()


def test_a_backwards_or_unparseable_range_is_a_400(client, auth, shop):
    owner = shop["owner"]

    assert _get(client, auth, owner,
                **{"from": "2026-06-30", "to": "2026-06-01"}
                ).status_code == 400
    assert _get(client, auth, owner, **{"from": "last tuesday"}
                ).status_code == 400


def test_orders_per_day_covers_the_whole_range_including_empty_days(
    client, auth, shop
):
    store, customer = shop["store"], shop["customer"]

    _place(store, customer, [(shop["zaatar"], 3.50, 1)], status="delivered",
           on=date(2026, 6, 10))
    _place(store, customer, [(shop["zaatar"], 3.50, 2)], status="delivered",
           on=date(2026, 6, 20))
    _place(store, customer, [(shop["zaatar"], 3.50, 1)], status="pending",
           on=date(2026, 6, 20))

    body = _get(client, auth, shop["owner"], **RANGE).get_json()
    series = body["orders_per_day"]

    assert len(series) == 30
    assert series[0]["date"] == "2026-06-01"
    assert series[-1]["date"] == "2026-06-30"

    by_date = {row["date"]: row["orders"] for row in series}
    assert by_date["2026-06-10"] == 1
    assert by_date["2026-06-20"] == 2
    assert by_date["2026-06-11"] == 0

    assert body["busiest_day"] == {"date": "2026-06-20", "orders": 2}


# --------------------------------------------------------------------------- #
# Top products
# --------------------------------------------------------------------------- #

def test_top_by_units_and_top_by_revenue_are_different_orders(
    client, auth, shop
):
    """The interesting case: the thing that sells most is not the thing
    that earns most, which is the whole reason for two tables."""
    store, customer = shop["store"], shop["customer"]

    # 10 x 3.50 = 35.00 — the most units, middling money.
    _place(store, customer, [(shop["zaatar"], 3.50, 10)], status="delivered",
           on=TODAY)
    # 4 x 14.00 = 56.00 — fewer units, the most money.
    _place(store, customer, [(shop["nuts"], 14.00, 4)], status="delivered",
           on=TODAY)
    # 6 x 12.00 = 72.00 — most money of all, middling units.
    _place(store, customer, [(shop["oil"], 12.00, 6)], status="delivered",
           on=TODAY)

    body = _get(client, auth, shop["owner"], **RANGE).get_json()

    by_units = [row["id"] for row in body["top_products_by_units"]]
    by_revenue = [row["id"] for row in body["top_products_by_revenue"]]

    assert by_units == [shop["zaatar"].id, shop["oil"].id, shop["nuts"].id]
    assert by_revenue == [shop["oil"].id, shop["nuts"].id, shop["zaatar"].id]
    assert by_units != by_revenue

    assert body["top_products_by_units"][0]["units"] == 10
    assert body["top_products_by_revenue"][0]["revenue"] == "72.00"


def test_top_products_exclude_cancelled_orders(client, auth, shop):
    store, customer = shop["store"], shop["customer"]

    _place(store, customer, [(shop["zaatar"], 3.50, 50)], status="canceled",
           on=TODAY)
    _place(store, customer, [(shop["oil"], 12.00, 1)], status="delivered",
           on=TODAY)

    body = _get(client, auth, shop["owner"], **RANGE).get_json()

    assert [row["id"] for row in body["top_products_by_units"]] == [
        shop["oil"].id
    ]


def test_top_products_are_capped_at_five(client, auth, shop, make_product):
    store, customer = shop["store"], shop["customer"]

    for n in range(7):
        product = make_product(store=store, price=5.00, stock=100)
        _place(store, customer, [(product, 5.00, n + 1)],
               status="delivered", on=TODAY)

    body = _get(client, auth, shop["owner"], **RANGE).get_json()

    assert len(body["top_products_by_units"]) == 5
    assert len(body["top_products_by_revenue"]) == 5


# --------------------------------------------------------------------------- #
# Best rated
# --------------------------------------------------------------------------- #

def test_best_rated_needs_two_reviews_so_one_five_star_cannot_top_it(
    client, auth, shop
):
    """A single perfect review is one customer's opinion, not a rating."""
    shop["zaatar"].rating_avg = Decimal("5.00")
    shop["zaatar"].rating_count = 1
    shop["oil"].rating_avg = Decimal("4.20")
    shop["oil"].rating_count = 9
    _db.session.commit()

    body = _get(client, auth, shop["owner"], **RANGE).get_json()
    rated = body["best_rated_products"]

    assert [row["id"] for row in rated] == [shop["oil"].id]
    assert rated[0]["rating_count"] == 9


def test_best_rated_is_ordered_by_average_once_the_minimum_is_met(
    client, auth, shop
):
    shop["zaatar"].rating_avg = Decimal("4.90")
    shop["zaatar"].rating_count = 2
    shop["oil"].rating_avg = Decimal("4.20")
    shop["oil"].rating_count = 9
    _db.session.commit()

    rated = _get(
        client, auth, shop["owner"], **RANGE
    ).get_json()["best_rated_products"]

    assert [row["id"] for row in rated] == [
        shop["zaatar"].id, shop["oil"].id
    ]


# --------------------------------------------------------------------------- #
# Scope — a security test, not a feature test
# --------------------------------------------------------------------------- #

def test_a_vendor_sees_only_their_own_store(
    client, auth, shop, make_store, make_product, make_user
):
    mine, customer = shop["store"], shop["customer"]

    _place(mine, customer, [(shop["oil"], 12.00, 2)], status="delivered",
           on=TODAY, delivery_fee="3.00")

    rival = make_store()
    rival_product = make_product(store=rival, price=99.00, stock=100)
    _place(rival, customer, [(rival_product, 99.00, 7)], status="delivered",
           on=TODAY, delivery_fee="9.00")

    ours = _get(client, auth, shop["owner"], **RANGE).get_json()
    theirs = _get(client, auth, rival.owner, **RANGE).get_json()

    assert ours["store"]["id"] == mine.id
    assert theirs["store"]["id"] == rival.id

    # The figures differ, so neither is quietly reading the whole table.
    assert ours["money"]["collected"]["revenue"] == "24.00"
    assert theirs["money"]["collected"]["revenue"] == "693.00"
    assert ours["totals"]["units_sold"] == 2
    assert theirs["totals"]["units_sold"] == 7

    # And no row from one store appears anywhere in the other's payload.
    mine_ids = {shop["oil"].id, shop["zaatar"].id, shop["nuts"].id}

    for table in ("top_products_by_units", "top_products_by_revenue",
                  "best_rated_products"):
        assert all(row["id"] != rival_product.id for row in ours[table])
        assert all(row["id"] not in mine_ids for row in theirs[table])


def test_a_vendor_cannot_ask_for_another_store_by_id(
    client, auth, shop, make_store, make_product, make_user
):
    """There is no parameter for it, and adding one to the query string
    changes nothing — the store comes from the token."""
    rival = make_store()
    rival_product = make_product(store=rival, price=99.00, stock=100)
    _place(rival, shop["customer"], [(rival_product, 99.00, 7)],
           status="delivered", on=TODAY)

    body = _get(
        client, auth, shop["owner"],
        store_id=rival.id, **RANGE
    ).get_json()

    assert body["store"]["id"] == shop["store"].id
    assert body["money"]["collected"]["revenue"] == "0.00"


def test_a_customer_cannot_reach_the_dashboard(client, auth, make_user):
    assert _get(
        client, auth, make_user("customer")
    ).status_code == 403


def test_a_vendor_with_no_store_gets_a_404(client, auth, make_user):
    assert _get(client, auth, make_user("vendor")).status_code == 404


# --------------------------------------------------------------------------- #
# Empty and thin
# --------------------------------------------------------------------------- #

def test_a_store_with_no_orders_returns_zeros_and_no_error(
    client, auth, shop
):
    response = _get(client, auth, shop["owner"], **RANGE)

    assert response.status_code == 200
    body = response.get_json()

    assert body["has_orders"] is False
    assert body["totals"] == {
        "orders": 0,
        "units_sold": 0,
        "average_order_value": "0.00",
    }

    for bucket in ("collected", "in_progress"):
        assert body["money"][bucket] == {
            "orders": 0,
            "units": 0,
            "goods_sold": "0.00",
            "discounts": "0.00",
            "revenue": "0.00",
            "delivery": "0.00",
        }

    assert body["orders_by_status"] == {
        "pending": 0, "processing": 0, "delivered": 0, "canceled": 0
    }
    assert body["top_products_by_units"] == []
    assert body["top_products_by_revenue"] == []
    assert body["best_rated_products"] == []
    assert body["busiest_day"] is None

    # The axis is still complete, so the chart has a shape rather than
    # being an empty box.
    assert len(body["orders_per_day"]) == 30
    assert all(row["orders"] == 0 for row in body["orders_per_day"])


def test_an_average_over_no_delivered_orders_is_zero_not_a_crash(
    client, auth, shop
):
    _place(shop["store"], shop["customer"], [(shop["oil"], 12.00, 1)],
           status="pending", on=TODAY)

    body = _get(client, auth, shop["owner"], **RANGE).get_json()

    assert body["totals"]["average_order_value"] == "0.00"
    assert body["has_orders"] is True


# --------------------------------------------------------------------------- #
# Shape of the work
# --------------------------------------------------------------------------- #

def test_the_query_count_does_not_grow_with_the_number_of_orders(shop):
    """Every figure is an aggregate, so a busy store costs no more round
    trips than a quiet one. This is what stops a loop over orders from
    being added later without anyone noticing."""
    from sqlalchemy import event

    store, customer = shop["store"], shop["customer"]

    def count_statements():
        seen = []

        def listen(conn, cursor, statement, params, context, many):
            seen.append(statement)

        event.listen(_db.engine, "before_cursor_execute", listen)
        try:
            analytics_service.store_dashboard(
                store, RANGE["from"], RANGE["to"]
            )
        finally:
            event.remove(_db.engine, "before_cursor_execute", listen)

        return len(seen)

    _place(store, customer, [(shop["oil"], 12.00, 1)], status="delivered",
           on=TODAY)
    with_one = count_statements()

    for day in range(2, 26):
        _place(store, customer,
               [(shop["oil"], 12.00, 1), (shop["zaatar"], 3.50, 2)],
               status="delivered", on=date(2026, 6, day),
               delivery_fee="2.00", discount="1.00")

    with_many = count_statements()

    assert with_one == with_many
