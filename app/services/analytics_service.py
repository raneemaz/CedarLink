"""Vendor dashboard figures — one store, one period, one query per figure.

Every number here is produced by an aggregate the database runs. Nothing
loops over orders in Python: a store with three years of history is the
same number of round trips as a store with three orders.

**Scope.** Every query filters on ``Order.store_id``. There is no
unscoped path into this module — :func:`store_dashboard` takes a store,
not a store id, and the route resolves that store from the caller's own
ownership. An analytics endpoint that forgets its scope is a data
disclosure, not a bug.

**Money.** The order's money is stored, so it is read rather than
recomputed: ``order_items.unit_price`` is the price at the time of sale,
``coupon_redemptions.amount_applied`` is what the coupon actually took
off, and ``orders.delivery_fee`` is what was charged for delivery. No
pricing rule runs again here — a dashboard that re-derives a price is a
second place for the price to be wrong.

**What is revenue.** The store's revenue is *goods sold minus discounts
given*. The delivery fee is not the store's money — it is collected on
the store's behalf and settled with the driver — so it is reported
separately as a pass-through and never added into revenue.

**Collected vs in progress.** CedarLink is cash on delivery: the money
arrives when the order does. So delivered orders are *collected* and
pending/processing orders are *in progress*, and the two are never added
together. A cancelled order is in neither — it appears only in the
status breakdown, where the vendor can see it happened.

Deliberately absent, both because the data does not exist rather than
because the query would be hard:

* a cash/card split — checkout writes no ``Payment`` row and calls no
  provider, so every order is cash on delivery and a split would chart
  a distinction the system does not record;
* store or product view counts — there is no view table, and adding one
  means a write on every page load, which is a performance and
  visitor-privacy decision nobody has made.
"""

from datetime import date, datetime, timedelta, time, timezone
from decimal import Decimal
from zoneinfo import ZoneInfo

from sqlalchemy import Numeric, cast, func, select

from app.extensions import db
from app.models.coupon_redemption import CouponRedemption
from app.models.order import Order
from app.models.order_item import OrderItem
from app.models.product import Product

BEIRUT = ZoneInfo("Asia/Beirut")

# Money arrives at the door, so these are the orders whose money is in the
# vendor's hand. Everything else is either still coming or never coming.
COLLECTED_STATUSES = ("delivered",)
IN_PROGRESS_STATUSES = ("pending", "processing")
CANCELED_STATUS = "canceled"

# Every status the breakdown reports, in the order the interface shows
# them — the lifecycle, with the dead end last.
STATUSES = ("pending", "processing", "delivered", CANCELED_STATUS)

DEFAULT_RANGE_DAYS = 30

# A vendor asking for a decade would get a decade of daily buckets to
# render. The cap is generous and exists so the response size is bounded.
MAX_RANGE_DAYS = 366

# Below this, an average is one customer's opinion rather than a rating.
MIN_REVIEWS_FOR_BEST_RATED = 2

TOP_PRODUCTS_LIMIT = 5

ZERO = Decimal("0.00")


class AnalyticsError(ValueError):
    """An invalid dashboard range — the route returns it as 400."""


# --------------------------------------------------------------------------- #
# Dates
#
# The vendor thinks in Beirut days, and `created_at` is naive UTC (ADR
# 0013), so the range is resolved as local dates and converted to UTC
# instants for the WHERE clause.
# --------------------------------------------------------------------------- #

def _today_local():
    return datetime.now(BEIRUT).date()


def _parse_date(value, field):
    if value is None:
        return None

    if not isinstance(value, str):
        raise AnalyticsError(f"{field} must be a date as YYYY-MM-DD")

    try:
        return date.fromisoformat(value.strip())
    except ValueError:
        raise AnalyticsError(f"'{value}' is not a date as YYYY-MM-DD")


def resolve_range(from_value=None, to_value=None):
    """``(from_date, to_date)`` as inclusive Beirut-local dates.

    Defaults to the last :data:`DEFAULT_RANGE_DAYS` days ending today.
    Either bound may be given alone; the other keeps its default
    relationship to it.
    """
    start = _parse_date(from_value, "from")
    end = _parse_date(to_value, "to")

    if end is None:
        end = _today_local() if start is None else (
            start + timedelta(days=DEFAULT_RANGE_DAYS - 1)
        )

    if start is None:
        start = end - timedelta(days=DEFAULT_RANGE_DAYS - 1)

    if start > end:
        raise AnalyticsError("'from' must not be after 'to'")

    if (end - start).days + 1 > MAX_RANGE_DAYS:
        raise AnalyticsError(
            f"A range may cover at most {MAX_RANGE_DAYS} days"
        )

    return start, end


def _utc_bounds(start, end):
    """The half-open naive-UTC interval covering those local days.

    ``ZoneInfo`` resolves the offset for each specific instant, so a range
    that straddles a DST change gets the right boundary on both sides
    rather than one fixed offset applied to both.
    """
    begin_local = datetime.combine(start, time.min, tzinfo=BEIRUT)
    # Half-open: midnight at the start of the day *after* `end`, so the
    # last day is included whole without any 23:59:59.999 arithmetic.
    after_local = datetime.combine(
        end + timedelta(days=1), time.min, tzinfo=BEIRUT
    )

    return (
        begin_local.astimezone(timezone.utc).replace(tzinfo=None),
        after_local.astimezone(timezone.utc).replace(tzinfo=None),
    )


def _bucket_offset_hours(end):
    """Hours to add to a UTC timestamp to get the Beirut wall-clock day.

    Read from ``ZoneInfo`` at the end of the range rather than hardcoded,
    so it is +2 in winter and +3 in summer. A range that spans a DST
    transition uses the newer offset throughout, which misfiles orders
    placed in the one changed hour on the far side of it — a bounded and
    documented inaccuracy, and the price of keeping this to one aggregate
    query per figure.
    """
    at = datetime.combine(end, time(12, 0), tzinfo=BEIRUT)
    return int(at.utcoffset().total_seconds() // 3600)


# --------------------------------------------------------------------------- #
# Helpers
# --------------------------------------------------------------------------- #

def _money(value):
    """Any SUM() result as a 2-decimal ``Decimal``. NULL (no rows) is 0.00."""
    if value is None:
        return ZERO
    if not isinstance(value, Decimal):
        value = Decimal(str(value))
    return value.quantize(ZERO)


def _in_range(store, start_utc, end_utc):
    """The scope clause every query in this module starts from."""
    return (
        Order.store_id == store.id,
        Order.created_at >= start_utc,
        Order.created_at < end_utc,
    )


# `quantity * unit_price` has no declared type, so the SUM comes back as a
# float on SQLite. Casting keeps it Decimal all the way out of the driver.
_LINE_TOTAL = cast(OrderItem.quantity * OrderItem.unit_price, Numeric(10, 2))


# --------------------------------------------------------------------------- #
# The figures
# --------------------------------------------------------------------------- #

def _orders_and_delivery_by_status(store, start_utc, end_utc):
    """Order count and delivery fee per status. One grouped query."""
    rows = db.session.execute(
        select(
            Order.status,
            func.count(Order.id),
            func.sum(Order.delivery_fee),
            func.sum(Order.total_price),
        )
        .where(*_in_range(store, start_utc, end_utc))
        .group_by(Order.status)
    ).all()

    return {
        status: {
            "orders": count,
            "delivery": _money(delivery),
            "total_charged": _money(total),
        }
        for status, count, delivery, total in rows
    }


def _goods_and_units_by_status(store, start_utc, end_utc):
    """Goods value and unit count per status. One grouped query."""
    rows = db.session.execute(
        select(
            Order.status,
            func.sum(_LINE_TOTAL),
            func.sum(OrderItem.quantity),
        )
        .join(OrderItem, OrderItem.order_id == Order.id)
        .where(*_in_range(store, start_utc, end_utc))
        .group_by(Order.status)
    ).all()

    return {
        status: {"goods": _money(goods), "units": units or 0}
        for status, goods, units in rows
    }


def _discounts_by_status(store, start_utc, end_utc):
    """Coupon value given away per status. One grouped query.

    An inner join, so orders with no coupon simply do not appear — which
    is what a missing key means to the caller: nothing given away.
    """
    rows = db.session.execute(
        select(
            Order.status,
            func.sum(CouponRedemption.amount_applied),
        )
        .join(CouponRedemption, CouponRedemption.order_id == Order.id)
        .where(*_in_range(store, start_utc, end_utc))
        .group_by(Order.status)
    ).all()

    return {status: _money(amount) for status, amount in rows}


def _bucket(statuses, by_status, goods_units, discounts):
    """Fold the three per-status aggregates into one reportable block."""
    orders = sum(by_status.get(s, {}).get("orders", 0) for s in statuses)
    units = sum(goods_units.get(s, {}).get("units", 0) for s in statuses)

    goods = sum(
        (goods_units.get(s, {}).get("goods", ZERO) for s in statuses), ZERO
    )
    discount = sum((discounts.get(s, ZERO) for s in statuses), ZERO)
    delivery = sum(
        (by_status.get(s, {}).get("delivery", ZERO) for s in statuses), ZERO
    )

    return {
        "orders": orders,
        "units": units,
        "goods_sold": goods,
        "discounts": discount,
        # The store's own money. Delivery is deliberately not in this sum.
        "revenue": goods - discount,
        # Collected on the driver's behalf and settled with them. Reported
        # so the vendor can reconcile, never counted as income.
        "delivery": delivery,
    }


def _top_products(store, start_utc, end_utc, order_by):
    """Top 5 sold products by one measure. One query per measure.

    Two queries rather than one sorted twice in Python: the top five by
    units and the top five by revenue are different questions, and each is
    an ORDER BY the database can answer without shipping every product.
    Cancelled orders are excluded — those goods came back.
    """
    units = func.sum(OrderItem.quantity).label("units")
    revenue = func.sum(_LINE_TOTAL).label("revenue")

    measure = units if order_by == "units" else revenue

    rows = db.session.execute(
        select(
            Product.id,
            Product.name_en,
            Product.name_ar,
            Product.name_fr,
            units,
            revenue,
        )
        .join(OrderItem, OrderItem.product_id == Product.id)
        .join(Order, Order.id == OrderItem.order_id)
        .where(*_in_range(store, start_utc, end_utc))
        .where(Order.status != CANCELED_STATUS)
        .group_by(Product.id)
        .order_by(measure.desc(), Product.id)
        .limit(TOP_PRODUCTS_LIMIT)
    ).all()

    return [
        {
            "id": pid,
            "name_en": name_en,
            "name_ar": name_ar,
            "name_fr": name_fr,
            "units": qty or 0,
            "revenue": _money(money),
        }
        for pid, name_en, name_ar, name_fr, qty, money in rows
    ]


def _best_rated_products(store):
    """Top 5 by stored rating, two reviews minimum. One query.

    ``rating_avg`` and ``rating_count`` are maintained by ``review_service``
    (ADR 0015), so this reads them rather than recomputing an average.

    Not filtered by the period: a rating is a standing fact about the
    product, and a store with no orders this month has not stopped being
    well rated. The minimum keeps a single five-star review from topping
    a list above a product with forty reviews at 4.8.
    """
    rows = db.session.execute(
        select(
            Product.id,
            Product.name_en,
            Product.name_ar,
            Product.name_fr,
            Product.rating_avg,
            Product.rating_count,
        )
        .where(
            Product.store_id == store.id,
            Product.deleted_at.is_(None),
            Product.rating_count >= MIN_REVIEWS_FOR_BEST_RATED,
        )
        .order_by(Product.rating_avg.desc(), Product.rating_count.desc())
        .limit(TOP_PRODUCTS_LIMIT)
    ).all()

    return [
        {
            "id": pid,
            "name_en": name_en,
            "name_ar": name_ar,
            "name_fr": name_fr,
            "rating_avg": float(avg) if avg is not None else None,
            "rating_count": count or 0,
        }
        for pid, name_en, name_ar, name_fr, avg, count in rows
    ]


def _orders_per_day(store, start_utc, end_utc, start, end):
    """Order count for every day in the range, zeros included. One query.

    The query returns only the days that have orders; the zero-filling is
    a walk over the range itself, not over orders, so a store with no
    orders still gets a complete axis instead of an empty chart.
    """
    offset = _bucket_offset_hours(end)

    day = func.date(Order.created_at, f"{offset:+d} hours").label("day")

    rows = db.session.execute(
        select(day, func.count(Order.id))
        .where(*_in_range(store, start_utc, end_utc))
        .group_by(day)
    ).all()

    counts = {str(bucket): count for bucket, count in rows}

    series = []
    cursor = start
    while cursor <= end:
        key = cursor.isoformat()
        series.append({"date": key, "orders": counts.get(key, 0)})
        cursor += timedelta(days=1)

    return series


def _busiest_day(series):
    """The fullest day in the range, or ``None`` if nothing was ordered.

    Taken from the per-day aggregate rather than asked for separately —
    the answer is already in hand, and a second query for the maximum of a
    list we are holding would be a query for nothing. Ties go to the
    earliest day.
    """
    best = max(series, key=lambda row: row["orders"], default=None)

    if best is None or best["orders"] == 0:
        return None

    return dict(best)


# --------------------------------------------------------------------------- #
# The dashboard
# --------------------------------------------------------------------------- #

def store_dashboard(store, from_value=None, to_value=None):
    """Every dashboard figure for one store over one period.

    ``store`` is a resolved :class:`Store`, never an id — the caller has
    already established that it belongs to them.
    """
    start, end = resolve_range(from_value, to_value)
    start_utc, end_utc = _utc_bounds(start, end)

    by_status = _orders_and_delivery_by_status(store, start_utc, end_utc)
    goods_units = _goods_and_units_by_status(store, start_utc, end_utc)
    discounts = _discounts_by_status(store, start_utc, end_utc)

    collected = _bucket(
        COLLECTED_STATUSES, by_status, goods_units, discounts
    )
    in_progress = _bucket(
        IN_PROGRESS_STATUSES, by_status, goods_units, discounts
    )

    orders_by_status = {
        status: by_status.get(status, {}).get("orders", 0)
        for status in STATUSES
    }

    total_orders = sum(orders_by_status.values())

    # Sold, so cancelled units are not in it — those goods came back.
    units_sold = collected["units"] + in_progress["units"]

    # On the same basis as the headline revenue: what a completed sale is
    # worth to the store, delivery excluded. Zero orders, zero average —
    # never a division by nothing.
    average_order_value = (
        (collected["revenue"] / collected["orders"]).quantize(ZERO)
        if collected["orders"]
        else ZERO
    )

    series = _orders_per_day(store, start_utc, end_utc, start, end)

    return {
        "store": {"id": store.id, "name": store.name},
        "range": {
            "from": start.isoformat(),
            "to": end.isoformat(),
            "days": (end - start).days + 1,
        },
        "totals": {
            "orders": total_orders,
            "units_sold": units_sold,
            "average_order_value": average_order_value,
        },
        # Never summed together by anything that renders this.
        "money": {"collected": collected, "in_progress": in_progress},
        "orders_by_status": orders_by_status,
        "top_products_by_units": _top_products(
            store, start_utc, end_utc, "units"
        ),
        "top_products_by_revenue": _top_products(
            store, start_utc, end_utc, "revenue"
        ),
        "best_rated_products": _best_rated_products(store),
        "busiest_day": _busiest_day(series),
        "orders_per_day": series,
        # The one thing the interface cannot work out for itself: no
        # orders at all is a different screen, not a screen of zeros.
        "has_orders": total_orders > 0,
    }


def serialize(dashboard):
    """The dashboard as JSON — every Decimal as a fixed 2-decimal string.

    A string, not a float: money crosses the wire the way it is stored,
    and the client formats it rather than rounding it.
    """
    def money(value):
        return f"{value:.2f}"

    def bucket(data):
        return {
            "orders": data["orders"],
            "units": data["units"],
            "goods_sold": money(data["goods_sold"]),
            "discounts": money(data["discounts"]),
            "revenue": money(data["revenue"]),
            "delivery": money(data["delivery"]),
        }

    return {
        **dashboard,
        "totals": {
            **dashboard["totals"],
            "average_order_value": money(
                dashboard["totals"]["average_order_value"]
            ),
        },
        "money": {
            "collected": bucket(dashboard["money"]["collected"]),
            "in_progress": bucket(dashboard["money"]["in_progress"]),
        },
        "top_products_by_units": [
            {**row, "revenue": money(row["revenue"])}
            for row in dashboard["top_products_by_units"]
        ],
        "top_products_by_revenue": [
            {**row, "revenue": money(row["revenue"])}
            for row in dashboard["top_products_by_revenue"]
        ],
    }
