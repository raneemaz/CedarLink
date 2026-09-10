"""V-1 — the variant-level stock decrement must not oversell either.

This is a **new proof for a new code path**, not a re-run of CL-06.
``order_service._reserve_variant_stock`` is a deliberately separate
conditional statement from the product-level ``_reserve_stock`` the CL-06
barrier test in ``test_concurrent_checkout.py`` covers:
``UPDATE product_variants SET stock = stock - :qty
  WHERE id = :id AND stock >= :qty``.
So exactly as many concurrent checkouts of one variant succeed as there
are units of that variant, whatever the interleaving.

Same determinism as CL-06: every checkout thread is held at a barrier the
instant it has finished pricing — reads done, nothing written, no lock
held — then all released together.
"""

import threading

from flask_jwt_extended import create_access_token

import app.services.order_service as order_service
from app.extensions import db
from app.models.cart import Cart
from app.models.cart_item import CartItem
from app.models.product import Product
from app.models.product_variant import ProductVariant


def _put_variant_in_cart(user, product, variant, quantity):
    cart = Cart(user_id=user.id)
    db.session.add(cart)
    db.session.flush()
    db.session.add(
        CartItem(
            cart_id=cart.id,
            product_id=product.id,
            variant_id=variant.id,
            quantity=quantity,
        )
    )
    db.session.commit()


def _run_concurrent_checkouts(app, monkeypatch, buyers):
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


def test_two_checkouts_for_the_last_variant_unit_only_one_succeeds(
    app, monkeypatch, make_product, make_variant, make_user
):
    product = make_product(stock=0, price=10.0)
    variant = make_variant(product, label="Red", price=25.0, stock=1)

    buyers = [
        (name, make_user("customer", email=f"vrace-{name}@test.local"))
        for name in ("a", "b")
    ]
    for _, user in buyers:
        _put_variant_in_cart(user, product, variant, 1)

    results = _run_concurrent_checkouts(app, monkeypatch, buyers)

    assert sorted(results.values()) == [201, 400], results
    db.session.expire_all()
    assert db.session.get(ProductVariant, variant.id).stock == 0
    # The product's own stock was never touched by the variant path.
    assert db.session.get(Product, product.id).stock == 0


def test_three_checkouts_against_variant_stock_of_two_two_succeed(
    app, monkeypatch, make_product, make_variant, make_user
):
    product = make_product(stock=0, price=10.0)
    variant = make_variant(product, label="Blue", price=25.0, stock=2)

    buyers = [
        (name, make_user("customer", email=f"vrush-{name}@test.local"))
        for name in ("a", "b", "c")
    ]
    for _, user in buyers:
        _put_variant_in_cart(user, product, variant, 1)

    results = _run_concurrent_checkouts(app, monkeypatch, buyers)

    assert sorted(results.values()) == [201, 201, 400], results
    db.session.expire_all()
    assert db.session.get(ProductVariant, variant.id).stock == 0
