"""ADR 0033 §1 follow-up — the four abuse-path endpoints are throttled.

Limits (per user, falling back to IP), chosen against what `auth_routes.py`
uses (5–10/min) and what a real session looks like:

* `POST /api/cart/coupon`   — 10/min, 40/hour. The /hour cap is the
  enumeration guard for the distinct rejection reasons.
* `POST /api/orders`        — 8/min, 30/hour. Financial-cost path.
* `POST /api/reviews`       — 6/min, 20/hour. Spam / manipulation.
* review report             — 10/min, 30/hour.

Cart mutations, the notifications endpoints and `GET /api/exchange-rates`
stay unthrottled — see ADR 0033.
"""

import pytest


@pytest.fixture()
def stocked_cart(make_user, make_product, add_to_cart, auth):
    user = make_user("customer", email="rl-shopper@sec.local")
    product = make_product(stock=999)
    add_to_cart(user, product, 1)
    return user, product


def test_apply_coupon_is_rate_limited_and_keeps_distinct_reasons(
    client, auth, rate_limiting, stocked_cart
):
    from datetime import datetime, timedelta, timezone
    from app.extensions import db
    from app.models.coupon import Coupon

    user, _ = stocked_cart
    db.session.add(Coupon(
        code="EXPIRED", discount_type="fixed", value=10, is_active=True,
        ends_at=datetime.now(timezone.utc).replace(tzinfo=None)
        - timedelta(days=1),
    ))
    db.session.commit()
    headers = auth(user)

    # Distinct reasons survive: unknown vs expired are different codes.
    unknown = client.post(
        "/api/cart/coupon", json={"code": "NOPE"}, headers=headers
    )
    expired = client.post(
        "/api/cart/coupon", json={"code": "EXPIRED"}, headers=headers
    )
    assert 400 <= unknown.status_code < 500
    assert 400 <= expired.status_code < 500
    assert unknown.get_json()["code"] == "coupon_unknown"
    assert expired.get_json()["code"] == "coupon_expired"

    statuses = [
        client.post(
            "/api/cart/coupon", json={"code": f"X{i}"}, headers=headers
        ).status_code
        for i in range(14)
    ]
    assert 429 in statuses, statuses


def test_checkout_is_rate_limited(
    client, auth, rate_limiting, make_user, make_product, add_to_cart
):
    user = make_user("customer", email="rl-checkout@sec.local")
    product = make_product(stock=999)
    headers = auth(user)

    statuses = []
    for _ in range(12):
        add_to_cart(user, product, 1)
        statuses.append(
            client.post(
                "/api/orders",
                json={
                    "delivery_address": "1 St", "delivery_city": "Beirut",
                    "payment_method": "cash_on_delivery",
                },
                headers=headers,
            ).status_code
        )
    assert 429 in statuses, statuses


def test_create_review_is_rate_limited(
    client, auth, rate_limiting, make_user, make_product, make_order
):
    reviewer = make_user("customer", email="rl-reviewer@sec.local")
    headers = auth(reviewer)
    product = make_product(stock=999)
    orders = [
        make_order(customer=reviewer, product=product, status="delivered")
        for _ in range(10)
    ]

    statuses = [
        client.post(
            "/api/reviews",
            json={
                "product_id": product.id, "order_id": orders[i].id,
                "rating": 5, "title": "t", "body": "body text",
            },
            headers=headers,
        ).status_code
        for i in range(10)
    ]
    assert 429 in statuses, statuses


def test_report_review_is_rate_limited(
    client, auth, rate_limiting, make_user, make_product, make_order
):
    from app.extensions import db
    from app.models.review import Review

    author = make_user("customer", email="rl-author@sec.local")
    reviews = []
    for _ in range(14):
        product = make_product(stock=999)
        order = make_order(
            customer=author, product=product, status="delivered"
        )
        r = Review(
            user_id=author.id, order_id=order.id, product_id=product.id,
            rating=3, title="t", body="b",
        )
        db.session.add(r)
        db.session.flush()
        reviews.append(r.id)
    db.session.commit()

    reporter = make_user("customer", email="rl-reporter@sec.local")
    headers = auth(reporter)
    statuses = [
        client.post(
            f"/api/reviews/{rid}/report",
            json={"reason": "spam"}, headers=headers,
        ).status_code
        for rid in reviews
    ]
    assert 429 in statuses, statuses
