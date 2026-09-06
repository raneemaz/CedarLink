"""A02 / A01 — one customer cannot reach another customer's rows by id.

Orders, addresses, notifications and saved cards are all keyed to the
caller's own id in the service or route layer; a cross-tenant id must come
back 403 or 404 (never 200 carrying someone else's data, and never a 500).

The id-bearing customer routes are pulled from ``app.url_map`` and matched
by pattern, so a new ``/api/<thing>/<int:id>`` route that forgets the
ownership check fails ``test_no_unclassified_customer_id_route`` until it is
either classified here or fixed.
"""

import re

import pytest

# (rule regex, how to build the "other customer's" id, [(method, body), ...])
CUSTOMER_RESOURCE_ROUTES = [
    (r"^/api/orders/<int:id>$", "order", [("GET", None)]),
    (r"^/api/orders/<int:id>/cancel$", "order", [("PATCH", None)]),
    (
        r"^/api/orders/<int:id>/status$", "order",
        [("PATCH", {"status": "processing"})],
    ),
    (r"^/api/orders/<int:order_id>/reviewable$", "order", [("GET", None)]),
    (
        r"^/api/addresses/<int:address_id>$", "address",
        [
            ("GET", None),
            ("PUT", {"label": "x", "recipient_name": "x", "phone": "+9613",
                     "address_line": "x", "city": "Beirut"}),
            ("DELETE", None),
        ],
    ),
    (
        r"^/api/addresses/<int:address_id>/default$", "address",
        [("PATCH", None)],
    ),
    (
        r"^/api/notifications/<int:notification_id>/read$",
        "notification", [("PATCH", None)],
    ),
    (
        r"^/api/payment-methods/<int:payment_method_id>$", "payment_method",
        [
            ("GET", None),
            ("PUT", {"label": "x", "brand": "Visa", "last4": "4242"}),
            ("DELETE", None),
        ],
    ),
    (
        r"^/api/payment-methods/<int:payment_method_id>/default$",
        "payment_method", [("PATCH", None)],
    ),
]

# Routes that take an <int:id> but are not a per-customer resource, so they
# are out of scope for this file (covered elsewhere or public).
NOT_CUSTOMER_SCOPED = {
    r"^/api/users/<int:user_id>",          # self-id checked in its own tests
    r"^/api/stores/",                      # vendor isolation file
    r"^/api/products/<int:id>",            # public read / vendor write
    r"^/api/products/<int:product_id>/",   # public read / vendor write
    r"^/api/admin/",                       # admin file
    r"^/api/categories/<int:id>$",         # admin file
    r"^/api/reviews/<int:review_id>",      # author-scoped, own tests
    r"^/api/delivery/assignments/<int:id>",
    r"^/api/payments/<int:payment_id>$",
    r"^/api/cart/items/<int:item_id>$",    # cart is 1:1 with the caller
    r"^/api/stores/<int:store_id>/",
    r"^/api/payments/webhook/<string:provider>$",  # provider secret, not a user
}


@pytest.fixture()
def two_customers(make_user, make_order, make_product, client, auth):
    """Customer A (the attacker) and Customer B, with B owning one of
    everything addressable by id."""
    from app.extensions import db
    from app.models.address import Address
    from app.models.notification import Notification
    from app.models.payment_method import PaymentMethod

    a = make_user("customer", email="attacker@iso.local")
    b = make_user("customer", email="victim@iso.local")

    product = make_product(stock=5)
    b_order = make_order(customer=b, product=product, status="delivered")

    b_address = Address(
        user_id=b.id, label="Home", recipient_name="B", phone="+9613",
        address_line="1 Victim St", city="Beirut",
    )
    b_notification = Notification(
        user_id=b.id, category="order_updates", type="order_placed",
        title="B's order", message="private",
    )
    b_card = PaymentMethod(
        user_id=b.id, type="card", label="B Visa", brand="Visa", last4="4242",
    )
    db.session.add_all([b_address, b_notification, b_card])
    db.session.commit()

    return {
        "attacker": a,
        "ids": {
            "order": b_order.id,
            "address": b_address.id,
            "notification": b_notification.id,
            "payment_method": b_card.id,
        },
    }


def _probe(client, method, path, headers, body=None):
    return client.open(
        path, method=method, headers=headers, json=body or {}
    )


def test_a_customer_cannot_touch_another_customers_resources(
    client, auth, two_customers
):
    headers = auth(two_customers["attacker"])
    ids = two_customers["ids"]
    failures = []

    for rule_re, kind, method_bodies in CUSTOMER_RESOURCE_ROUTES:
        victim_id = ids[kind]
        path = re.sub(r"<[^>]+>", str(victim_id), rule_re.strip("^$"))
        for method, body in method_bodies:
            resp = _probe(client, method, path, headers, body)
            if resp.status_code not in (403, 404):
                failures.append(
                    f"{method} {path} -> {resp.status_code} "
                    f"(expected 403/404) body={resp.get_data(as_text=True)[:120]}"
                )

    assert not failures, "cross-tenant access leaked:\n" + "\n".join(failures)


def test_the_victim_can_still_reach_their_own(client, auth, make_user,
                                              make_order, make_product):
    """Control: the checks above are refusing the attacker, not everyone."""
    from app.extensions import db
    from app.models.address import Address

    b = make_user("customer", email="owner@iso.local")
    product = make_product(stock=5)
    order = make_order(customer=b, product=product, status="delivered")
    address = Address(
        user_id=b.id, label="Home", recipient_name="B", phone="+9613",
        address_line="1 St", city="Beirut",
    )
    db.session.add(address)
    db.session.commit()

    headers = auth(b)
    assert client.get(f"/api/orders/{order.id}", headers=headers).status_code \
        == 200
    assert client.get(
        f"/api/addresses/{address.id}", headers=headers
    ).status_code == 200


def test_no_unclassified_customer_id_route(app):
    """Rot guard: every `/api/.../<int:id>` route is either a classified
    per-customer resource (tested above) or explicitly out of scope. A new
    one lands here until someone decides which."""
    classified = {rule_re for rule_re, _, _ in CUSTOMER_RESOURCE_ROUTES}
    unclassified = []

    for rule in app.url_map.iter_rules():
        path = str(rule.rule)
        if not path.startswith("/api/"):
            continue
        if "<int:" not in path and "<string:" not in path:
            continue
        norm = "^" + path + "$"
        if norm in classified:
            continue
        if any(re.match(pat, path) for pat in NOT_CUSTOMER_SCOPED):
            continue
        unclassified.append(f"{sorted(rule.methods - {'HEAD', 'OPTIONS'})} {path}")

    assert not unclassified, (
        "id-bearing routes not classified for customer isolation "
        "(add to CUSTOMER_RESOURCE_ROUTES or NOT_CUSTOMER_SCOPED):\n"
        + "\n".join(unclassified)
    )
