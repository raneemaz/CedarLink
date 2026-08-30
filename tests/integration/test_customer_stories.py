"""Customer user stories from CedarLink.md.

- create an account
- browse stores / search products
- filter products by category, price, keyword; filter stores by location
- add products to a cart across multiple stores
- place an order (splits per store; decrements stock)
- view order history (own orders only)
- cancel a pending order
"""

from decimal import Decimal

from app.extensions import db
from app.models.order import Order
from app.models.product import Product

FIXED_CODE = "424242"


def _checkout(client, headers, city="Beirut"):
    return client.post(
        "/api/orders",
        json={
            "delivery_address": "1 Test Street",
            "delivery_city": city,
            "payment_method": "cash_on_delivery",
        },
        headers=headers,
    )


# --- create an account ---------------------------------------------------- #

def test_register_verify_login_full_flow(client, monkeypatch):
    """The only test that walks register -> verify -> login -> verify for real."""
    monkeypatch.setattr(
        "app.services.two_factor_service._generate_verification_code",
        lambda: FIXED_CODE,
    )

    reg = client.post(
        "/api/auth/register",
        json={
            "first_name": "Nadia",
            "last_name": "Khoury",
            "email": "nadia@example.com",
            "phone": "+961 3 111111",
            "password": "Passw0rd!",
            "verification_method": "email",
        },
    )
    assert reg.status_code == 201
    challenge_token = reg.get_json()["challenge_token"]

    verify = client.post(
        "/api/auth/register/verify",
        json={"challenge_token": challenge_token, "code": FIXED_CODE},
    )
    assert verify.status_code == 200
    assert verify.get_json()["user"]["role"] == "customer"
    assert "access_token" in verify.get_json()

    login = client.post(
        "/api/auth/login",
        json={"email": "nadia@example.com", "password": "Passw0rd!"},
    )
    assert login.status_code == 202
    login_token = login.get_json()["challenge_token"]

    login_verify = client.post(
        "/api/auth/login/verify",
        json={"challenge_token": login_token, "code": FIXED_CODE},
    )
    assert login_verify.status_code == 200
    assert "access_token" in login_verify.get_json()


def test_wrong_verification_code_is_rejected(client, monkeypatch):
    monkeypatch.setattr(
        "app.services.two_factor_service._generate_verification_code",
        lambda: FIXED_CODE,
    )
    reg = client.post(
        "/api/auth/register",
        json={
            "first_name": "A",
            "last_name": "B",
            "email": "ab@example.com",
            "phone": "+961 3 222222",
            "password": "Passw0rd!",
            "verification_method": "email",
        },
    )
    token = reg.get_json()["challenge_token"]
    bad = client.post(
        "/api/auth/register/verify",
        json={"challenge_token": token, "code": "000000"},
    )
    assert bad.status_code == 400


# --- browse / search / filter ------------------------------------------- #

def test_logged_out_visitor_can_browse_products(client, make_product):
    make_product(name="Zaatar", stock=10)
    make_product(name="Olive Oil", stock=4)

    resp = client.get("/api/products")

    assert resp.status_code == 200
    body = resp.get_json()
    assert body["total"] == 2
    assert {p["name"] for p in body["products"]} == {"Zaatar", "Olive Oil"}


def test_products_filter_by_category(client, make_store, make_category, make_product):
    store = make_store()
    food = make_category("Food")
    books = make_category("Books")
    make_product(store=store, category=food, name="Zaatar")
    make_product(store=store, category=books, name="Poems")

    resp = client.get(f"/api/products?category_id={food.id}")

    names = [p["name"] for p in resp.get_json()["products"]]
    assert names == ["Zaatar"]


def test_products_filter_by_price_range(client, make_store, make_product):
    store = make_store()
    make_product(store=store, name="Cheap", price=5.0)
    make_product(store=store, name="Mid", price=15.0)
    make_product(store=store, name="Pricey", price=50.0)

    resp = client.get("/api/products?min_price=10&max_price=20")

    names = [p["name"] for p in resp.get_json()["products"]]
    assert names == ["Mid"]


def test_products_filter_by_keyword(client, make_store, make_product):
    store = make_store()
    make_product(store=store, name="Cotton Keffiyeh")
    make_product(store=store, name="Wool Scarf")

    resp = client.get("/api/products?keyword=keffiyeh")

    names = [p["name"] for p in resp.get_json()["products"]]
    assert names == ["Cotton Keffiyeh"]


def test_stores_filter_by_location(client, make_store):
    make_store(name="Beirut Store", location="Beirut")
    make_store(name="Tripoli Store", location="Tripoli")

    resp = client.get("/api/stores?location=tripoli")

    assert resp.status_code == 200
    names = [s["name"] for s in resp.get_json()["stores"]]
    assert names == ["Tripoli Store"]


def test_customer_can_browse_store_directory(client, make_store):
    make_store(name="Open Store")

    resp = client.get("/api/stores")

    assert resp.status_code == 200
    assert any(s["name"] == "Open Store" for s in resp.get_json()["stores"])


# --- cart + checkout --------------------------------------------------- #

def test_cart_with_two_stores_creates_two_orders(
    client, auth, add_to_cart, make_product, customer
):
    p_a = make_product(name="From store A", stock=5)
    p_b = make_product(name="From store B", stock=5)
    assert p_a.store_id != p_b.store_id

    add_to_cart(customer, p_a, 1)
    add_to_cart(customer, p_b, 2)

    resp = _checkout(client, auth(customer))

    assert resp.status_code == 201
    orders = resp.get_json()["orders"]
    assert len(orders) == 2
    assert {o["store_id"] for o in orders} == {p_a.store_id, p_b.store_id}


def test_checkout_decrements_stock(
    client, auth, add_to_cart, make_product, customer
):
    product = make_product(stock=5)
    add_to_cart(customer, product, 2)

    resp = _checkout(client, auth(customer))
    assert resp.status_code == 201

    db.session.expire_all()
    assert db.session.get(Product, product.id).stock == 3


def test_checkout_total_is_exact_not_float_drifted(
    client, auth, add_to_cart, make_store, make_product, customer
):
    # 0.10 * 3 = 0.30 exactly; float arithmetic gives 0.30000000000000004.
    store = make_store(
        location="Beirut",
        inside_city_delivery_fee=0,
        outside_city_delivery_fee=0,
    )
    product = make_product(store=store, price=Decimal("0.10"), stock=10)
    add_to_cart(customer, product, 3)

    quote = client.post(
        "/api/orders/preview",
        json={"delivery_city": "Beirut"},
        headers=auth(customer),
    ).get_json()
    assert quote["total"] == 0.3
    assert quote["subtotal"] == 0.3

    resp = _checkout(client, auth(customer))
    assert resp.status_code == 201
    order = resp.get_json()["orders"][0]
    assert order["subtotal"] == 0.3
    assert order["total_price"] == 0.3

    db.session.expire_all()
    assert db.session.get(Order, order["id"]).total_price == Decimal("0.30")


def test_checkout_with_empty_cart_is_rejected(client, auth, customer):
    resp = _checkout(client, auth(customer))
    assert resp.status_code == 400


def test_checkout_more_than_stock_is_rejected(
    client, auth, add_to_cart, make_product, customer
):
    product = make_product(stock=1)
    # cart-add caps at stock, so force an over-quantity item directly.
    from app.models.cart import Cart
    from app.models.cart_item import CartItem

    cart = Cart(user_id=customer.id)
    db.session.add(cart)
    db.session.flush()
    db.session.add(
        CartItem(cart_id=cart.id, product_id=product.id, quantity=5)
    )
    db.session.commit()

    resp = _checkout(client, auth(customer))
    assert resp.status_code == 400
    assert "stock" in resp.get_json()["error"].lower()


def test_multi_store_checkout_failure_rolls_back_all_reservations(
    client, auth, add_to_cart, make_product, customer
):
    # Store A has enough stock; store B does not. The whole checkout must
    # fail without touching store A's stock.
    from app.models.cart import Cart
    from app.models.cart_item import CartItem

    ok = make_product(name="In stock", stock=10)
    short = make_product(name="Almost gone", stock=1)
    assert ok.store_id != short.store_id

    cart = Cart(user_id=customer.id)
    db.session.add(cart)
    db.session.flush()
    db.session.add(CartItem(cart_id=cart.id, product_id=ok.id, quantity=3))
    db.session.add(CartItem(cart_id=cart.id, product_id=short.id, quantity=5))
    db.session.commit()

    resp = _checkout(client, auth(customer))
    assert resp.status_code == 400

    db.session.expire_all()
    assert db.session.get(Product, ok.id).stock == 10
    assert db.session.get(Product, short.id).stock == 1
    assert Order.query.count() == 0


# --- order history --------------------------------------------------- #

def test_order_history_shows_only_own_orders(
    client, auth, make_order, make_user
):
    alice = make_user("customer", email="alice@test.local")
    bob = make_user("customer", email="bob@test.local")
    make_order(customer=alice)
    make_order(customer=alice)
    make_order(customer=bob)

    resp = client.get("/api/orders", headers=auth(alice))

    assert resp.status_code == 200
    orders = resp.get_json()["orders"]
    assert len(orders) == 2
    assert all(o["id"] for o in orders)


def test_viewing_another_customers_order_is_forbidden(
    client, auth, make_order, make_user
):
    owner = make_user("customer", email="owner@test.local")
    intruder = make_user("customer", email="intruder@test.local")
    order = make_order(customer=owner)

    resp = client.get(f"/api/orders/{order.id}", headers=auth(intruder))

    assert resp.status_code == 403


# --- cancellation --------------------------------------------------- #

def test_cancelling_pending_order_restores_stock(
    client, auth, make_product, make_order, customer
):
    product = make_product(stock=5)
    order = make_order(
        customer=customer, product=product, quantity=2, decrement_stock=True
    )
    assert db.session.get(Product, product.id).stock == 3

    resp = client.patch(
        f"/api/orders/{order.id}/cancel", headers=auth(customer)
    )

    assert resp.status_code == 200
    db.session.expire_all()
    assert db.session.get(Order, order.id).status == "canceled"
    assert db.session.get(Product, product.id).stock == 5


def test_cancelling_processing_order_is_rejected(
    client, auth, make_product, make_order, customer
):
    product = make_product(stock=5)
    order = make_order(
        customer=customer,
        product=product,
        quantity=2,
        status="processing",
        decrement_stock=True,
    )

    resp = client.patch(
        f"/api/orders/{order.id}/cancel", headers=auth(customer)
    )

    assert resp.status_code == 400
    db.session.expire_all()
    assert db.session.get(Order, order.id).status == "processing"
    assert db.session.get(Product, product.id).stock == 3
