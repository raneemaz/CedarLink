"""Coupons — pricing, eligibility, redemption and scope.

The properties that matter: the discount is computed server-side from the
coupon record, it comes off the goods and never the delivery fee, a total
never goes negative, a use cannot be taken twice, and a vendor cannot reach
past their own store. See docs/decisions/0021-coupons-and-discounts.md.
"""

import threading
from datetime import datetime, timedelta, timezone
from decimal import Decimal

from flask_jwt_extended import create_access_token

from app.extensions import db
from app.models.coupon import Coupon
from app.models.coupon_redemption import CouponRedemption
from app.services import coupon_service

PREVIEW_URL = "/api/orders/preview"
ORDERS_URL = "/api/orders"
CART_COUPON_URL = "/api/cart/coupon"

CITY = "Beirut"


def _utc(**delta):
    return datetime.now(timezone.utc).replace(tzinfo=None) + timedelta(**delta)


def make_coupon(**kw):
    """A coupon row. Percentage/10% platform-wide unless told otherwise."""
    coupon = Coupon(
        code=coupon_service.normalize_code(kw.get("code", "SAVE10")),
        discount_type=kw.get("discount_type", "percentage"),
        value=Decimal(str(kw.get("value", "10"))),
        min_order_total=(
            None if kw.get("min_order_total") is None
            else Decimal(str(kw["min_order_total"]))
        ),
        starts_at=kw.get("starts_at"),
        ends_at=kw.get("ends_at"),
        usage_limit=kw.get("usage_limit"),
        per_user_limit=kw.get("per_user_limit"),
        used_count=kw.get("used_count", 0),
        store_id=kw.get("store_id"),
        is_active=kw.get("is_active", True),
    )
    db.session.add(coupon)
    db.session.commit()
    return coupon


def _preview(client, auth, user, code=None, city=CITY):
    body = {"delivery_city": city}
    if code is not None:
        body["coupon_code"] = code
    return client.post(PREVIEW_URL, json=body, headers=auth(user))


def _checkout(client, auth, user, code=None, extra=None):
    body = {
        "delivery_address": "1 Test Street",
        "delivery_city": CITY,
        "payment_method": "cash_on_delivery",
    }
    if code is not None:
        body["coupon_code"] = code
    if extra:
        body.update(extra)
    return client.post(ORDERS_URL, json=body, headers=auth(user))


def _store_group(quote, store_id):
    return next(g for g in quote["stores"] if g["store_id"] == store_id)


# --------------------------------------------------------------------------- #
# The discount itself
# --------------------------------------------------------------------------- #

def test_a_percentage_comes_off_the_goods_subtotal(
    client, auth, customer, make_product, add_to_cart
):
    product = make_product(price=Decimal("50.00"), stock=10)
    add_to_cart(customer, product, 2)
    make_coupon(code="SAVE10", discount_type="percentage", value="10")

    quote = _preview(client, auth, customer, "SAVE10").get_json()

    assert quote["subtotal"] == 100.00
    assert quote["discount"] == 10.00
    assert quote["coupon_code"] == "SAVE10"
    assert quote["total"] == 100.00 - 10.00 + quote["delivery_fee"]


def test_a_fixed_amount_comes_off_the_goods_subtotal(
    client, auth, customer, make_product, add_to_cart
):
    product = make_product(price=Decimal("50.00"), stock=10)
    add_to_cart(customer, product, 2)
    make_coupon(code="TAKE15", discount_type="fixed", value="15")

    quote = _preview(client, auth, customer, "TAKE15").get_json()

    assert quote["subtotal"] == 100.00
    assert quote["discount"] == 15.00
    assert quote["total"] == 100.00 - 15.00 + quote["delivery_fee"]


def test_the_delivery_fee_is_never_discounted(
    client, auth, customer, make_store, make_product, add_to_cart
):
    """A delivery fee is a real cost the store carries whatever the goods
    were sold for."""
    store = make_store(inside_city_delivery_fee=7, outside_city_delivery_fee=9)
    product = make_product(store=store, price=Decimal("40.00"), stock=10)
    add_to_cart(customer, product, 1)
    # 100% off: if the fee were reachable, this is where it would vanish.
    make_coupon(code="ALLOFF", discount_type="percentage", value="100")

    quote = _preview(client, auth, customer, "ALLOFF").get_json()

    assert quote["subtotal"] == 40.00
    assert quote["discount"] == 40.00
    assert quote["delivery_fee"] == 7.00
    assert quote["total"] == 7.00

    group = _store_group(quote, store.id)
    assert group["discount"] == 40.00
    assert group["delivery_fee"] == 7.00
    assert group["total"] == 7.00


def test_the_total_clamps_and_never_goes_negative(
    client, auth, customer, make_store, make_product, add_to_cart
):
    store = make_store(inside_city_delivery_fee=0, outside_city_delivery_fee=0)
    product = make_product(store=store, price=Decimal("10.00"), stock=10)
    add_to_cart(customer, product, 1)
    # A fixed amount far larger than the goods.
    make_coupon(code="HUGE", discount_type="fixed", value="500")

    quote = _preview(client, auth, customer, "HUGE").get_json()

    assert quote["subtotal"] == 10.00
    assert quote["discount"] == 10.00, "the discount clamps to the goods"
    assert quote["total"] == 0.00
    assert quote["total"] >= 0


def test_min_order_total_is_measured_before_the_discount(
    client, auth, customer, make_product, add_to_cart
):
    """Otherwise a coupon could pull a basket under its own minimum and
    still apply."""
    product = make_product(price=Decimal("50.00"), stock=10)
    add_to_cart(customer, product, 1)

    # Subtotal 50, minimum 50: passes on the pre-discount figure. A 20%
    # discount would leave 40, under the minimum — it must still apply.
    make_coupon(
        code="MIN50", discount_type="percentage", value="20",
        min_order_total="50",
    )

    quote = _preview(client, auth, customer, "MIN50").get_json()
    assert quote["discount"] == 10.00

    # One cent under the minimum is refused.
    db.session.query(Coupon).filter_by(code="MIN50").update(
        {"min_order_total": Decimal("50.01")}
    )
    db.session.commit()

    refused = _preview(client, auth, customer, "MIN50")
    assert refused.status_code == 400
    assert refused.get_json()["code"] == coupon_service.BELOW_MINIMUM


# --------------------------------------------------------------------------- #
# Rejection reasons — one code each
# --------------------------------------------------------------------------- #

def test_an_unknown_code_has_its_own_error_code(
    client, auth, customer, product, add_to_cart
):
    add_to_cart(customer, product, 1)

    response = _preview(client, auth, customer, "NOSUCHCODE")
    assert response.status_code == 404
    assert response.get_json()["code"] == coupon_service.UNKNOWN


def test_an_inactive_code_has_its_own_error_code(
    client, auth, customer, product, add_to_cart
):
    add_to_cart(customer, product, 1)
    make_coupon(code="OFF", is_active=False)

    response = _preview(client, auth, customer, "OFF")
    assert response.status_code == 400
    assert response.get_json()["code"] == coupon_service.INACTIVE


def test_a_not_yet_started_code_has_its_own_error_code(
    client, auth, customer, product, add_to_cart
):
    add_to_cart(customer, product, 1)
    make_coupon(code="SOON", starts_at=_utc(days=1))

    response = _preview(client, auth, customer, "SOON")
    assert response.status_code == 400
    assert response.get_json()["code"] == coupon_service.NOT_STARTED


def test_an_expired_code_has_its_own_error_code(
    client, auth, customer, product, add_to_cart
):
    add_to_cart(customer, product, 1)
    make_coupon(code="GONE", ends_at=_utc(days=-1))

    response = _preview(client, auth, customer, "GONE")
    assert response.status_code == 400
    assert response.get_json()["code"] == coupon_service.EXPIRED


def test_every_rejection_reason_is_a_distinct_code():
    """The point of per-reason codes is that they differ."""
    codes = [
        coupon_service.UNKNOWN,
        coupon_service.INACTIVE,
        coupon_service.NOT_STARTED,
        coupon_service.EXPIRED,
        coupon_service.BELOW_MINIMUM,
        coupon_service.USAGE_LIMIT,
        coupon_service.USER_LIMIT,
        coupon_service.WRONG_STORE,
        coupon_service.FIXED_MULTI_STORE,
    ]
    assert len(set(codes)) == len(codes)


# --------------------------------------------------------------------------- #
# Scope across a multi-store cart
# --------------------------------------------------------------------------- #

def _two_store_cart(customer, make_store, make_product, add_to_cart):
    store_a = make_store(
        name="Store A", inside_city_delivery_fee=2, outside_city_delivery_fee=2
    )
    store_b = make_store(
        name="Store B", inside_city_delivery_fee=3, outside_city_delivery_fee=3
    )
    product_a = make_product(store=store_a, price=Decimal("100.00"), stock=10)
    product_b = make_product(store=store_b, price=Decimal("60.00"), stock=10)
    add_to_cart(customer, product_a, 1)
    add_to_cart(customer, product_b, 1)
    return store_a, store_b


def test_a_store_coupon_leaves_the_other_store_untouched(
    client, auth, customer, make_store, make_product, add_to_cart
):
    store_a, store_b = _two_store_cart(
        customer, make_store, make_product, add_to_cart
    )
    make_coupon(
        code="AONLY", discount_type="fixed", value="25", store_id=store_a.id
    )

    quote = _preview(client, auth, customer, "AONLY").get_json()

    group_a = _store_group(quote, store_a.id)
    group_b = _store_group(quote, store_b.id)

    assert group_a["discount"] == 25.00
    assert group_a["total"] == 100.00 - 25.00 + 2.00

    assert group_b["discount"] == 0.00
    assert group_b["total"] == 60.00 + 3.00

    assert quote["discount"] == 25.00
    assert quote["total"] == (100 - 25 + 2) + (60 + 3)


def test_a_store_coupon_for_a_store_not_in_the_cart_is_refused(
    client, auth, customer, make_store, make_product, add_to_cart
):
    store = make_store(name="In cart")
    other = make_store(name="Elsewhere")
    add_to_cart(customer, make_product(store=store, stock=5), 1)
    make_coupon(code="OTHER", store_id=other.id)

    response = _preview(client, auth, customer, "OTHER")
    assert response.status_code == 400
    assert response.get_json()["code"] == coupon_service.WRONG_STORE


def test_a_fixed_platform_coupon_is_refused_on_a_two_store_cart(
    client, auth, customer, make_store, make_product, add_to_cart
):
    """There is no defensible way to split a flat amount across two
    separate orders — ADR 0021."""
    _two_store_cart(customer, make_store, make_product, add_to_cart)
    make_coupon(code="FLAT20", discount_type="fixed", value="20")

    response = _preview(client, auth, customer, "FLAT20")
    assert response.status_code == 400
    assert response.get_json()["code"] == coupon_service.FIXED_MULTI_STORE


def test_a_fixed_platform_coupon_is_fine_on_a_single_store_cart(
    client, auth, customer, make_product, add_to_cart
):
    add_to_cart(customer, make_product(price=Decimal("80.00"), stock=5), 1)
    make_coupon(code="FLAT20", discount_type="fixed", value="20")

    quote = _preview(client, auth, customer, "FLAT20").get_json()
    assert quote["discount"] == 20.00


def test_a_percentage_platform_coupon_splits_across_stores_and_sums(
    client, auth, customer, make_store, make_product, add_to_cart
):
    """A percentage distributes without ambiguity: each store's share of
    the discount is its own subtotal's percentage, and the parts add up to
    the same number as taking the percentage off the whole basket."""
    store_a, store_b = _two_store_cart(
        customer, make_store, make_product, add_to_cart
    )
    make_coupon(code="TEN", discount_type="percentage", value="10")

    quote = _preview(client, auth, customer, "TEN").get_json()

    group_a = _store_group(quote, store_a.id)
    group_b = _store_group(quote, store_b.id)

    assert group_a["discount"] == 10.00      # 10% of 100
    assert group_b["discount"] == 6.00       # 10% of 60

    assert group_a["discount"] + group_b["discount"] == quote["discount"]
    assert quote["discount"] == 16.00        # 10% of the 160 subtotal
    assert quote["total"] == quote["subtotal"] - 16.00 + quote["delivery_fee"]


# --------------------------------------------------------------------------- #
# Matching
# --------------------------------------------------------------------------- #

def test_codes_match_case_insensitively_and_ignore_surrounding_space(
    client, auth, customer, make_product, add_to_cart
):
    add_to_cart(customer, make_product(price=Decimal("100.00"), stock=5), 1)
    coupon = make_coupon(code="  save10  ", discount_type="percentage",
                         value="10")

    assert coupon.code == "SAVE10", "stored trimmed and uppercased"

    for typed in ("save10", "SAVE10", "  SaVe10  ", "\tsave10\n"):
        quote = _preview(client, auth, customer, typed).get_json()
        assert quote["discount"] == 10.00, f"{typed!r} should have matched"


# --------------------------------------------------------------------------- #
# Redemption
# --------------------------------------------------------------------------- #

def test_checkout_records_a_redemption_and_increments_the_count(
    client, auth, customer, make_product, add_to_cart
):
    add_to_cart(customer, make_product(price=Decimal("100.00"), stock=5), 1)
    coupon = make_coupon(code="SAVE10", value="10")

    response = _checkout(client, auth, customer, "SAVE10")
    assert response.status_code == 201
    body = response.get_json()
    assert body["discount"] == 10.00
    assert body["coupon_code"] == "SAVE10"

    db.session.refresh(coupon)
    assert coupon.used_count == 1

    redemption = CouponRedemption.query.one()
    assert redemption.user_id == customer.id
    assert redemption.coupon_id == coupon.id
    assert redemption.amount_applied == Decimal("10.00")
    assert redemption.order_id == body["orders"][0]["id"]


def test_a_preview_redeems_nothing(
    client, auth, customer, make_product, add_to_cart
):
    add_to_cart(customer, make_product(price=Decimal("100.00"), stock=5), 1)
    coupon = make_coupon(code="SAVE10", value="10")

    for _ in range(3):
        assert _preview(client, auth, customer, "SAVE10").status_code == 200

    db.session.refresh(coupon)
    assert coupon.used_count == 0
    assert CouponRedemption.query.count() == 0


def test_per_user_limit_is_enforced_across_separate_orders(
    client, auth, customer, make_product, add_to_cart
):
    product = make_product(price=Decimal("100.00"), stock=10)
    make_coupon(code="ONCE", value="10", per_user_limit=1)

    add_to_cart(customer, product, 1)
    assert _checkout(client, auth, customer, "ONCE").status_code == 201

    add_to_cart(customer, product, 1)
    second = _checkout(client, auth, customer, "ONCE")
    assert second.status_code == 400
    assert second.get_json()["code"] == coupon_service.USER_LIMIT

    # The order itself still had to fail, not silently drop the coupon.
    assert CouponRedemption.query.count() == 1


def test_a_different_customer_is_not_blocked_by_someone_elses_use(
    client, auth, make_user, make_product, add_to_cart
):
    product = make_product(price=Decimal("100.00"), stock=10)
    make_coupon(code="ONCE", value="10", per_user_limit=1)

    first = make_user("customer", email="first@test.local")
    second = make_user("customer", email="second@test.local")

    add_to_cart(first, product, 1)
    assert _checkout(client, auth, first, "ONCE").status_code == 201

    add_to_cart(second, product, 1)
    assert _checkout(client, auth, second, "ONCE").status_code == 201


def test_the_usage_limit_is_enforced(
    client, auth, make_user, make_product, add_to_cart
):
    product = make_product(price=Decimal("100.00"), stock=10)
    make_coupon(code="LAST", value="10", usage_limit=1)

    first = make_user("customer", email="a@test.local")
    second = make_user("customer", email="b@test.local")

    add_to_cart(first, product, 1)
    assert _checkout(client, auth, first, "LAST").status_code == 201

    add_to_cart(second, product, 1)
    response = _checkout(client, auth, second, "LAST")
    assert response.status_code == 400
    assert response.get_json()["code"] == coupon_service.USAGE_LIMIT


def test_cancelling_a_pending_order_releases_the_redemption(
    client, auth, customer, make_product, add_to_cart
):
    """Same symmetry as restoring stock: the order gives back what it took."""
    product = make_product(price=Decimal("100.00"), stock=10)
    coupon = make_coupon(code="ONCE", value="10", usage_limit=1,
                         per_user_limit=1)

    add_to_cart(customer, product, 1)
    order_id = (
        _checkout(client, auth, customer, "ONCE")
        .get_json()["orders"][0]["id"]
    )

    db.session.refresh(coupon)
    assert coupon.used_count == 1

    canceled = client.patch(
        f"/api/orders/{order_id}/cancel", headers=auth(customer)
    )
    assert canceled.status_code == 200

    db.session.refresh(coupon)
    assert coupon.used_count == 0
    assert CouponRedemption.query.count() == 0

    # And the code works again.
    add_to_cart(customer, product, 1)
    assert _checkout(client, auth, customer, "ONCE").status_code == 201


def test_a_client_submitted_discount_in_the_body_is_ignored(
    client, auth, customer, make_product, add_to_cart
):
    """The amount is computed from the coupon record. Nothing the client
    sends is read, so nothing it sends can change the price."""
    add_to_cart(customer, make_product(price=Decimal("100.00"), stock=5), 1)
    make_coupon(code="SAVE10", value="10")

    response = _checkout(
        client, auth, customer, "SAVE10",
        extra={
            "discount": 99999,
            "total": 0,
            "total_price": 0,
            "subtotal": 0,
        },
    )
    assert response.status_code == 201

    body = response.get_json()
    assert body["discount"] == 10.00

    order = body["orders"][0]
    assert order["subtotal"] == 100.00
    assert order["discount"] == 10.00
    assert order["total_price"] == 100.00 - 10.00 + order["delivery_fee"]

    assert CouponRedemption.query.one().amount_applied == Decimal("10.00")


def test_two_concurrent_checkouts_against_one_use_admit_exactly_one(
    app, monkeypatch, make_user, make_product, add_to_cart
):
    """The usage limit is claimed in a single conditional UPDATE, so the
    interleaving cannot matter — ADR 0007, fourth appearance.

    Both buyers are held at a barrier the instant they have finished
    pricing: the coupon has been read and found usable, nothing is written
    yet, then both are released into the claim together.
    """
    import app.services.order_service as order_service

    product = make_product(price=Decimal("100.00"), stock=10)
    coupon = make_coupon(code="LAST", value="10", usage_limit=1)
    coupon_id = coupon.id

    buyers = [
        make_user("customer", email="race-a@test.local"),
        make_user("customer", email="race-b@test.local"),
    ]
    for buyer in buyers:
        add_to_cart(buyer, product, 1)

    headers = []
    for buyer in buyers:
        raw = create_access_token(
            identity=str(buyer.id), additional_claims={"role": buyer.role}
        )
        headers.append({"Authorization": f"Bearer {raw}"})

    real_price_cart = order_service.price_cart
    gate = threading.Barrier(len(buyers), timeout=15)

    def synced_price_cart(*args, **kwargs):
        pricing = real_price_cart(*args, **kwargs)
        try:
            gate.wait()
        except threading.BrokenBarrierError:
            pass
        return pricing

    monkeypatch.setattr(order_service, "price_cart", synced_price_cart)

    results = {}

    def do_checkout(index):
        results[index] = app.test_client().post(
            ORDERS_URL,
            json={
                "delivery_address": "1 Race Street",
                "delivery_city": CITY,
                "payment_method": "cash_on_delivery",
                "coupon_code": "LAST",
            },
            headers=headers[index],
        ).status_code

    threads = [
        threading.Thread(target=do_checkout, args=(i,))
        for i in range(len(buyers))
    ]
    for thread in threads:
        thread.start()
    for thread in threads:
        thread.join(timeout=20)

    assert sorted(results.values()) == [201, 400], (
        f"expected exactly one checkout to take the last use, got {results}"
    )

    assert db.session.get(Coupon, coupon_id).used_count == 1
    assert CouponRedemption.query.count() == 1


# --------------------------------------------------------------------------- #
# Cart endpoints
# --------------------------------------------------------------------------- #

def test_applying_a_coupon_holds_it_and_clearing_drops_it(
    client, auth, customer, make_product, add_to_cart
):
    add_to_cart(customer, make_product(price=Decimal("100.00"), stock=5), 1)
    make_coupon(code="SAVE10", value="10")

    applied = client.post(
        CART_COUPON_URL,
        json={"code": "save10", "delivery_city": CITY},
        headers=auth(customer),
    )
    assert applied.status_code == 200
    assert applied.get_json()["discount"] == 10.00

    # Held: a later quote that names no code still gets the discount.
    held = _preview(client, auth, customer).get_json()
    assert held["discount"] == 10.00
    assert held["coupon_code"] == "SAVE10"

    cleared = client.delete(CART_COUPON_URL, headers=auth(customer))
    assert cleared.status_code == 200

    after = _preview(client, auth, customer).get_json()
    assert after["discount"] == 0.00
    assert after["coupon_code"] is None


def test_applying_a_bad_coupon_does_not_hold_it(
    client, auth, customer, make_product, add_to_cart
):
    add_to_cart(customer, make_product(price=Decimal("100.00"), stock=5), 1)
    make_coupon(code="GONE", ends_at=_utc(days=-1))

    rejected = client.post(
        CART_COUPON_URL,
        json={"code": "GONE", "delivery_city": CITY},
        headers=auth(customer),
    )
    assert rejected.status_code == 400
    assert rejected.get_json()["code"] == coupon_service.EXPIRED

    assert _preview(client, auth, customer).get_json()["coupon_code"] is None


def test_checkout_spends_the_held_code(
    client, auth, customer, make_product, add_to_cart
):
    product = make_product(price=Decimal("100.00"), stock=10)
    make_coupon(code="SAVE10", value="10")
    add_to_cart(customer, product, 1)

    client.post(
        CART_COUPON_URL,
        json={"code": "SAVE10", "delivery_city": CITY},
        headers=auth(customer),
    )

    assert _checkout(client, auth, customer).get_json()["discount"] == 10.00

    # The next cart starts clean.
    add_to_cart(customer, product, 1)
    assert _preview(client, auth, customer).get_json()["coupon_code"] is None


# --------------------------------------------------------------------------- #
# Vendor and admin scope
# --------------------------------------------------------------------------- #

def test_a_vendor_cannot_create_a_platform_wide_coupon(
    client, auth, make_store
):
    """store_id comes from the URL and is never read from the body."""
    store = make_store()

    response = client.post(
        f"/api/stores/{store.id}/coupons",
        json={
            "code": "VENDORWIDE",
            "discount_type": "percentage",
            "value": 10,
            "store_id": None,          # ignored
        },
        headers=auth(store.owner),
    )
    assert response.status_code == 201

    created = Coupon.query.filter_by(code="VENDORWIDE").one()
    assert created.store_id == store.id
    assert created.is_platform_wide is False


def test_a_vendor_cannot_widen_a_coupon_by_editing_it(
    client, auth, make_store
):
    store = make_store()
    coupon = make_coupon(code="MINE", store_id=store.id)

    response = client.put(
        f"/api/stores/{store.id}/coupons/{coupon.id}",
        json={"store_id": None, "value": 20},
        headers=auth(store.owner),
    )
    assert response.status_code == 200

    db.session.refresh(coupon)
    assert coupon.store_id == store.id


def test_a_vendor_cannot_touch_another_stores_coupon(
    client, auth, make_store
):
    mine = make_store(name="Mine")
    theirs = make_store(name="Theirs")
    foreign = make_coupon(code="THEIRS", store_id=theirs.id)

    # Through my own store's collection: not found, not "forbidden" — the
    # coupon is not in it.
    assert client.put(
        f"/api/stores/{mine.id}/coupons/{foreign.id}",
        json={"value": 90},
        headers=auth(mine.owner),
    ).status_code == 404

    # Through theirs: rejected at ownership.
    assert client.put(
        f"/api/stores/{theirs.id}/coupons/{foreign.id}",
        json={"value": 90},
        headers=auth(mine.owner),
    ).status_code == 403

    assert client.delete(
        f"/api/stores/{mine.id}/coupons/{foreign.id}",
        headers=auth(mine.owner),
    ).status_code == 404

    db.session.refresh(foreign)
    assert foreign.value == Decimal("10.00")


def test_a_vendor_cannot_reach_a_platform_coupon_through_their_store(
    client, auth, make_store
):
    store = make_store()
    platform = make_coupon(code="PLATFORM")

    assert client.put(
        f"/api/stores/{store.id}/coupons/{platform.id}",
        json={"value": 90},
        headers=auth(store.owner),
    ).status_code == 404


def test_an_admin_creates_platform_wide_coupons(client, auth, admin):
    response = client.post(
        "/api/admin/coupons",
        json={"code": "welcome", "discount_type": "fixed", "value": 5},
        headers=auth(admin),
    )
    assert response.status_code == 201

    created = Coupon.query.filter_by(code="WELCOME").one()
    assert created.store_id is None
    assert created.is_platform_wide is True

    listed = client.get("/api/admin/coupons", headers=auth(admin)).get_json()
    assert [c["code"] for c in listed["coupons"]] == ["WELCOME"]


def test_a_customer_cannot_reach_the_admin_coupon_routes(
    client, auth, customer
):
    assert client.get(
        "/api/admin/coupons", headers=auth(customer)
    ).status_code == 403
    assert client.post(
        "/api/admin/coupons",
        json={"code": "X", "discount_type": "fixed", "value": 1},
        headers=auth(customer),
    ).status_code == 403


def test_a_redeemed_coupon_is_deactivated_rather_than_deleted(
    client, auth, admin, customer, make_product, add_to_cart
):
    """A redemption row is order history; the coupon it points at must not
    vanish underneath it."""
    add_to_cart(customer, make_product(price=Decimal("100.00"), stock=5), 1)
    coupon = make_coupon(code="SAVE10", value="10")
    assert _checkout(client, auth, customer, "SAVE10").status_code == 201

    response = client.delete(
        f"/api/admin/coupons/{coupon.id}", headers=auth(admin)
    )
    assert response.status_code == 200

    db.session.refresh(coupon)
    assert coupon.is_active is False
    assert CouponRedemption.query.count() == 1

    # Deactivated means unusable.
    add_to_cart(customer, make_product(price=Decimal("50.00"), stock=5), 1)
    refused = _preview(client, auth, customer, "SAVE10")
    assert refused.get_json()["code"] == coupon_service.INACTIVE


def test_an_unused_coupon_is_deleted_outright(client, auth, admin):
    coupon = make_coupon(code="NEVERUSED")

    assert client.delete(
        f"/api/admin/coupons/{coupon.id}", headers=auth(admin)
    ).status_code == 200
    assert Coupon.query.count() == 0


def test_a_duplicate_code_is_refused(client, auth, admin):
    make_coupon(code="TAKEN")

    response = client.post(
        "/api/admin/coupons",
        json={"code": "taken", "discount_type": "fixed", "value": 5},
        headers=auth(admin),
    )
    assert response.status_code == 400
    assert Coupon.query.count() == 1


def test_out_of_range_values_are_refused(client, auth, admin):
    for payload in (
        {"code": "A", "discount_type": "percentage", "value": 0},
        {"code": "B", "discount_type": "percentage", "value": 101},
        {"code": "C", "discount_type": "fixed", "value": 0},
        {"code": "D", "discount_type": "fixed", "value": -5},
        {"code": "E", "discount_type": "bogus", "value": 10},
    ):
        response = client.post(
            "/api/admin/coupons", json=payload, headers=auth(admin)
        )
        assert response.status_code == 400, payload

    assert Coupon.query.count() == 0
