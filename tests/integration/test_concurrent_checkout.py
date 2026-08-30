"""CL-06 — the checkout stock decrement is check-then-write with no
conditional UPDATE, so two checkouts for the last unit can both succeed.

This test is xfail(strict=True): it fails today (both succeed) and must
start passing the moment 4c makes the decrement atomic — strict xfail turns
that into a CI failure so the change can't land silently.
"""

import threading

import pytest
from sqlalchemy.orm import Session

from app.extensions import db
from app.models.cart import Cart
from app.models.cart_item import CartItem
from app.models.order import Order
from app.models.order_item import OrderItem


def _put_in_cart(user, product, quantity):
    cart = Cart(user_id=user.id)
    db.session.add(cart)
    db.session.flush()
    db.session.add(
        CartItem(cart_id=cart.id, product_id=product.id, quantity=quantity)
    )
    db.session.commit()


@pytest.mark.xfail(
    strict=True,
    reason="CL-06: stock decrement is check-then-write, not a conditional UPDATE",
)
def test_concurrent_checkout_does_not_oversell(
    app, monkeypatch, make_product, make_user
):
    product = make_product(stock=1, price=10.0)
    buyer_a = make_user("customer", email="race-a@test.local")
    buyer_b = make_user("customer", email="race-b@test.local")
    _put_in_cart(buyer_a, product, 1)
    _put_in_cart(buyer_b, product, 1)

    from flask_jwt_extended import create_access_token

    def token(user):
        with app.app_context():
            raw = create_access_token(
                identity=str(user.id),
                additional_claims={"role": user.role},
            )
        return {"Authorization": f"Bearer {raw}"}

    # Force both checkouts to read the product before either commits, so
    # they both pass the stock check against stock == 1.
    main_thread = threading.current_thread()
    barrier = threading.Barrier(2, timeout=10)
    thread_state = threading.local()
    real_get = Session.get

    def synced_get(self, *args, **kwargs):
        if (
            threading.current_thread() is not main_thread
            and getattr(thread_state, "synced", False) is False
        ):
            thread_state.synced = True
            try:
                barrier.wait()
            except threading.BrokenBarrierError:
                pass
        return real_get(self, *args, **kwargs)

    monkeypatch.setattr(Session, "get", synced_get)

    results = {}

    def do_checkout(name, user):
        client = app.test_client()
        resp = client.post(
            "/api/orders",
            json={
                "delivery_address": "1 Race Street",
                "delivery_city": "Beirut",
                "payment_method": "cash_on_delivery",
            },
            headers=token(user),
        )
        results[name] = resp.status_code

    t_a = threading.Thread(target=do_checkout, args=("a", buyer_a))
    t_b = threading.Thread(target=do_checkout, args=("b", buyer_b))
    t_a.start()
    t_b.start()
    t_a.join(timeout=15)
    t_b.join(timeout=15)

    db.session.expire_all()
    orders = Order.query.filter_by(store_id=product.store_id).all()
    ordered_units = sum(
        item.quantity
        for order in orders
        for item in OrderItem.query.filter_by(order_id=order.id)
        if item.product_id == product.id
    )

    # Never sell more units than existed.
    assert ordered_units <= 1, (
        f"oversold: {ordered_units} units ordered from stock of 1 "
        f"(checkout results: {results})"
    )
