"""V-1 — buying a specific variant end to end (ADR 0035).

Proves: a variant line is quoted and charged at the resolved price, the
order item keeps the denormalised trilingual label, variant stock (not the
product's) is what moves, and a plain line and a variant line coexist in
one order without either code path disturbing the other.
"""

from app.extensions import db
from app.models.order import Order
from app.models.product import Product
from app.models.product_variant import ProductVariant

CITY = "Beirut"


def _checkout(client, auth, user):
    return client.post(
        "/api/orders",
        json={
            "delivery_address": "1 Race Street",
            "delivery_city": CITY,
            "payment_method": "cash_on_delivery",
        },
        headers=auth(user),
    )


def test_variant_line_is_quoted_and_charged_at_the_resolved_price(
    client, auth, make_store, make_category, make_product, make_variant,
    make_user,
):
    store = make_store()
    category = make_category()
    # The product's own price is the fall-back; the 2L variant overrides it.
    product = make_product(
        store=store, category=category, price=12.00, stock=0
    )
    variant = make_variant(
        product,
        label="2L",
        label_ar="٢ لتر",
        label_fr="2 L",
        price=22.00,
        stock=5,
    )
    customer = make_user("customer")

    added = client.post(
        "/api/cart/items",
        json={"product_id": product.id, "variant_id": variant.id,
              "quantity": 2},
        headers=auth(customer),
    )
    assert added.status_code == 200, added.get_json()

    preview = client.post(
        "/api/orders/preview",
        json={"delivery_city": CITY},
        headers=auth(customer),
    ).get_json()
    assert preview["subtotal"] == 44.0

    placed = _checkout(client, auth, customer)
    assert placed.status_code == 201, placed.get_json()

    order = Order.query.filter_by(user_id=customer.id).one()
    item = order.items[0]
    assert item.variant_id == variant.id
    assert float(item.unit_price) == 22.0
    assert item.variant_label_en == "2L"
    assert item.variant_label_ar == "٢ لتر"
    assert item.variant_label_fr == "2 L"

    # Variant stock moved; the product's own stock did not.
    db.session.expire_all()
    assert db.session.get(ProductVariant, variant.id).stock == 3
    assert db.session.get(Product, product.id).stock == 0

    body = client.get(
        f"/api/orders/{order.id}", headers=auth(customer)
    ).get_json()["order"]
    line = body["items"][0]
    assert line["variant_label"] == "2L"
    assert line["variant_label_fr"] == "2 L"
    assert line["unit_price"] == 22.0


def test_a_plain_line_and_a_variant_line_check_out_in_one_order(
    client, auth, make_store, make_category, make_product, make_variant,
    make_user,
):
    store = make_store()
    category = make_category()

    plain = make_product(
        store=store, category=category, price=10.00, stock=5
    )
    sized = make_product(
        store=store, category=category, price=12.00, stock=0
    )
    variant = make_variant(sized, label="1L", price=None, stock=4)

    customer = make_user("customer")

    for payload in (
        {"product_id": plain.id, "quantity": 1},
        {"product_id": sized.id, "variant_id": variant.id, "quantity": 1},
    ):
        resp = client.post(
            "/api/cart/items", json=payload, headers=auth(customer)
        )
        assert resp.status_code == 200, resp.get_json()

    placed = _checkout(client, auth, customer)
    assert placed.status_code == 201, placed.get_json()

    order = Order.query.filter_by(user_id=customer.id).one()
    by_product = {i.product_id: i for i in order.items}

    plain_item = by_product[plain.id]
    assert plain_item.variant_id is None
    assert plain_item.variant_label_en is None
    assert float(plain_item.unit_price) == 10.0

    variant_item = by_product[sized.id]
    assert variant_item.variant_id == variant.id
    # price=None on the variant → the product's price.
    assert float(variant_item.unit_price) == 12.0
    assert variant_item.variant_label_en == "1L"

    db.session.expire_all()
    assert db.session.get(Product, plain.id).stock == 4
    assert db.session.get(ProductVariant, variant.id).stock == 3


def test_choosing_no_option_on_a_variant_product_is_refused(
    client, auth, make_store, make_category, make_product, make_variant,
    make_user,
):
    store = make_store()
    product = make_product(
        store=store, category=make_category(), price=12.00, stock=9
    )
    make_variant(product, label="1L", stock=3)
    customer = make_user("customer")

    resp = client.post(
        "/api/cart/items",
        json={"product_id": product.id, "quantity": 1},
        headers=auth(customer),
    )
    assert resp.status_code == 400
    assert resp.get_json()["code"] == "variant_required"


def test_cancelling_a_variant_order_restores_variant_stock(
    client, auth, make_store, make_category, make_product, make_variant,
    make_user,
):
    store = make_store()
    product = make_product(
        store=store, category=make_category(), price=12.00, stock=0
    )
    variant = make_variant(product, label="2L", price=22.00, stock=3)
    customer = make_user("customer")

    client.post(
        "/api/cart/items",
        json={"product_id": product.id, "variant_id": variant.id,
              "quantity": 2},
        headers=auth(customer),
    )
    _checkout(client, auth, customer)

    db.session.expire_all()
    assert db.session.get(ProductVariant, variant.id).stock == 1

    order = Order.query.filter_by(user_id=customer.id).one()
    cancelled = client.patch(
        f"/api/orders/{order.id}/cancel", headers=auth(customer)
    )
    assert cancelled.status_code == 200, cancelled.get_json()

    db.session.expire_all()
    assert db.session.get(ProductVariant, variant.id).stock == 3


def test_a_product_with_no_options_is_unchanged(
    client, auth, make_store, make_category, make_product, make_user,
):
    """A product with zero option rows behaves exactly as before V-1 —
    plain add, plain checkout, no variant keys on the wire."""
    store = make_store()
    product = make_product(
        store=store, category=make_category(), price=8.00, stock=5
    )
    customer = make_user("customer")

    client.post(
        "/api/cart/items",
        json={"product_id": product.id, "quantity": 2},
        headers=auth(customer),
    )
    cart = client.get("/api/cart", headers=auth(customer)).get_json()
    line = cart["stores"][0]["items"][0]
    assert "variant_id" not in line and "variant_label" not in line

    _checkout(client, auth, customer)
    order = Order.query.filter_by(user_id=customer.id).one()
    assert order.items[0].variant_id is None

    detail = client.get(
        f"/api/products/{product.id}", headers=auth(customer)
    ).get_json()
    assert "options" not in detail and "variants" not in detail


def test_retired_variant_is_hidden_from_customers_shown_to_the_owner(
    client, auth, make_store, make_category, make_product, make_variant,
    make_user,
):
    """A non-owner's product detail lists only active variants; the owning
    vendor still sees the retired one to manage it (ADR 0036)."""
    vendor = make_user("vendor", email="retire-owner@test.local")
    store = make_store(owner=vendor)
    product = make_product(
        store=store, category=make_category(), price=12.00, stock=0
    )
    active = make_variant(product, label="1L", price=12.00, stock=5)
    retired = make_variant(product, label="2L", price=22.00, stock=5,
                           is_active=False)

    customer = make_user("customer", email="retire-cust@test.local")
    seen = client.get(
        f"/api/products/{product.id}", headers=auth(customer)
    ).get_json()
    ids = [v["id"] for v in seen["variants"]]
    assert ids == [active.id]

    owner_view = client.get(
        f"/api/products/{product.id}", headers=auth(vendor)
    ).get_json()
    owner_ids = sorted(v["id"] for v in owner_view["variants"])
    assert owner_ids == sorted([active.id, retired.id])
