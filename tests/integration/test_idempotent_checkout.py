"""Idempotency-Key on ``POST /api/orders`` — the double-click / retry guard.

A slow network can hide a real success from the client: the order is
placed, but the response never arrives, so the client (or the customer,
double-clicking "Place order") sends the exact same checkout request
again. Without protection this creates a second order -- and, once a real
payment provider is wired in, a second charge for the same cart.

The client attaches one ``Idempotency-Key`` header to every attempt of a
single logical checkout. These tests check the two halves of that
contract: a sequential retry replays the first response instead of
placing a second order, and two truly concurrent requests carrying the
same key -- the actual double-click -- still only place one.
"""

import threading

from flask_jwt_extended import create_access_token

from app.extensions import db
from app.models.cart import Cart
from app.models.cart_item import CartItem
from app.models.order import Order


def _put_in_cart(user, product, quantity=1):
    # A user has at most one cart (``carts.user_id`` is unique), and
    # checkout empties a cart's items without deleting the cart row
    # itself -- so a second call in the same test must reuse it, not
    # insert a second one.
    cart = Cart.query.filter_by(user_id=user.id).first()
    if cart is None:
        cart = Cart(user_id=user.id)
        db.session.add(cart)
        db.session.flush()
    db.session.add(
        CartItem(cart_id=cart.id, product_id=product.id, quantity=quantity)
    )
    db.session.commit()


def _checkout(client, auth_headers, idempotency_key=None):
    headers = dict(auth_headers)
    if idempotency_key:
        headers["Idempotency-Key"] = idempotency_key
    return client.post(
        "/api/orders",
        json={
            "delivery_address": "1 Cedar Street",
            "delivery_city": "Beirut",
            "payment_method": "cash_on_delivery",
        },
        headers=headers,
    )


def test_repeat_request_with_same_key_replays_first_response(
    client, auth, make_product, make_user
):
    buyer = make_user("customer")
    product = make_product(stock=5, price=10.0)
    _put_in_cart(buyer, product, 1)

    key = "checkout-attempt-1"
    headers = auth(buyer)

    first = _checkout(client, headers, key)
    assert first.status_code == 201, first.get_json()
    first_order_id = first.get_json()["orders"][0]["id"]

    # Same key again -- the client retrying after, say, a timed-out
    # response. Must come back with the *same* order, not a new one.
    second = _checkout(client, headers, key)
    assert second.status_code == 201, second.get_json()
    assert second.get_json() == first.get_json()
    assert second.get_json()["orders"][0]["id"] == first_order_id

    assert Order.query.filter_by(user_id=buyer.id).count() == 1


def test_different_keys_each_place_their_own_order(
    client, auth, make_product, make_user
):
    buyer = make_user("customer")
    product = make_product(stock=5, price=10.0)
    headers = auth(buyer)

    _put_in_cart(buyer, product, 1)
    first = _checkout(client, headers, "attempt-a")
    assert first.status_code == 201, first.get_json()

    _put_in_cart(buyer, product, 1)
    second = _checkout(client, headers, "attempt-b")
    assert second.status_code == 201, second.get_json()

    assert (
        first.get_json()["orders"][0]["id"]
        != second.get_json()["orders"][0]["id"]
    )
    assert Order.query.filter_by(user_id=buyer.id).count() == 2


def test_missing_key_is_unprotected_by_design(
    client, auth, make_product, make_user
):
    """No header at all -- e.g. an older client -- behaves exactly as
    before idempotency keys existed: every call is a new order. This is
    the documented, backward-compatible default (see
    app/utils/idempotency.py), not a gap to close here.
    """
    buyer = make_user("customer")
    product = make_product(stock=5, price=10.0)
    headers = auth(buyer)

    _put_in_cart(buyer, product, 1)
    first = _checkout(client, headers)
    assert first.status_code == 201, first.get_json()

    _put_in_cart(buyer, product, 1)
    second = _checkout(client, headers)
    assert second.status_code == 201, second.get_json()

    assert Order.query.filter_by(user_id=buyer.id).count() == 2


def test_concurrent_double_click_with_same_key_places_only_one_order(
    app, monkeypatch, make_product, make_user
):
    """The real double-click: two requests, same key, in flight together.

    One thread is held just past the point where it has claimed the key
    (inside the idempotency module, right before running checkout) until
    both threads have got there, then both are released -- so neither can
    win the race by simply running first.
    """
    import app.utils.idempotency as idempotency

    buyer = make_user("customer")
    product = make_product(stock=5, price=10.0)
    _put_in_cart(buyer, product, 1)

    gate = threading.Barrier(2, timeout=15)
    real_begin = idempotency.begin

    def synced_begin(*args, **kwargs):
        result = real_begin(*args, **kwargs)
        try:
            gate.wait()
        except threading.BrokenBarrierError:
            pass
        return result

    monkeypatch.setattr(idempotency, "begin", synced_begin)

    with app.app_context():
        raw = create_access_token(
            identity=str(buyer.id),
            additional_claims={"role": buyer.role},
        )
    headers = {"Authorization": f"Bearer {raw}"}

    results = {}

    def do_checkout(name):
        resp = app.test_client().post(
            "/api/orders",
            json={
                "delivery_address": "1 Cedar Street",
                "delivery_city": "Beirut",
                "payment_method": "cash_on_delivery",
            },
            headers={**headers, "Idempotency-Key": "double-click"},
        )
        results[name] = resp.status_code

    threads = [
        threading.Thread(target=do_checkout, args=(name,))
        for name in ("a", "b")
    ]
    for thread in threads:
        thread.start()
    for thread in threads:
        thread.join(timeout=20)

    # One request created the order (201); the other found the key
    # already claimed and backed off (409) rather than racing it.
    assert sorted(results.values()) == [201, 409], results

    db.session.expire_all()
    assert Order.query.filter_by(user_id=buyer.id).count() == 1
