"""CL-06 — checkout must not oversell under concurrent requests.

The stock decrement is a single conditional statement
(``UPDATE products SET stock = stock - :qty WHERE id = :id AND stock >= :qty``);
a rowcount of 0 is the out-of-stock error. So exactly as many concurrent
checkouts succeed as there are units, no matter the interleaving.

Determinism: every checkout thread is held at a barrier the instant it has
finished pricing — all the stock reads are done, nothing is written yet and
no lock is held — then all threads are released together. Whichever thread
reaches the write first commits; the rest see the decrement and fail
cleanly. No sleeps, no reliance on wall-clock scheduling.
"""

import threading

from flask_jwt_extended import create_access_token

import app.services.order_service as order_service
from app.extensions import db
from app.models.cart import Cart
from app.models.cart_item import CartItem
from app.models.order import Order
from app.models.order_item import OrderItem
from app.models.product import Product


def _put_in_cart(user, product, quantity):
    cart = Cart(user_id=user.id)
    db.session.add(cart)
    db.session.flush()
    db.session.add(
        CartItem(cart_id=cart.id, product_id=product.id, quantity=quantity)
    )
    db.session.commit()


def _run_concurrent_checkouts(app, monkeypatch, buyers):
    """Fire ``POST /api/orders`` from every buyer at once.

    Returns ``{name: status_code}``. All requests are held just past pricing
    (inside ``price_cart``) until every request has got there, so they all
    price against the same starting stock.
    """
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

    def token(user):
        with app.app_context():
            raw = create_access_token(
                identity=str(user.id),
                additional_claims={"role": user.role},
            )
        return {"Authorization": f"Bearer {raw}"}

    results = {}

    def do_checkout(name, user):
        resp = app.test_client().post(
            "/api/orders",
            json={
                "delivery_address": "1 Race Street",
                "delivery_city": "Beirut",
                "payment_method": "cash_on_delivery",
            },
            headers=token(user),
        )
        results[name] = resp.status_code

    threads = [
        threading.Thread(target=do_checkout, args=(name, user))
        for name, user in buyers
    ]
    for thread in threads:
        thread.start()
    for thread in threads:
        thread.join(timeout=20)

    return results


def _units_ordered(product):
    db.session.expire_all()
    order_ids = [
        order.id
        for order in Order.query.filter_by(store_id=product.store_id).all()
    ]
    if not order_ids:
        return 0
    return sum(
        item.quantity
        for item in OrderItem.query.filter(
            OrderItem.order_id.in_(order_ids),
            OrderItem.product_id == product.id,
        ).all()
    )


def test_two_checkouts_for_the_last_unit_only_one_succeeds(
    app, monkeypatch, make_product, make_user
):
    product = make_product(stock=1, price=10.0)
    buyers = [
        (name, make_user("customer", email=f"race-{name}@test.local"))
        for name in ("a", "b")
    ]
    for _, user in buyers:
        _put_in_cart(user, product, 1)

    results = _run_concurrent_checkouts(app, monkeypatch, buyers)

    assert sorted(results.values()) == [201, 400], results
    assert _units_ordered(product) == 1
    db.session.expire_all()
    assert db.session.get(Product, product.id).stock == 0


def test_three_checkouts_against_stock_of_two_two_succeed(
    app, monkeypatch, make_product, make_user
):
    product = make_product(stock=2, price=10.0)
    buyers = [
        (name, make_user("customer", email=f"rush-{name}@test.local"))
        for name in ("a", "b", "c")
    ]
    for _, user in buyers:
        _put_in_cart(user, product, 1)

    results = _run_concurrent_checkouts(app, monkeypatch, buyers)

    assert sorted(results.values()) == [201, 201, 400], results
    assert _units_ordered(product) == 2
    db.session.expire_all()
    assert db.session.get(Product, product.id).stock == 0
