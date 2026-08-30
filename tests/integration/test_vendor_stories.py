"""Store-owner / vendor user stories from CedarLink.md.

- register a store profile (self-registration + create store)
- a new store is pending until an admin approves it
- add products to the OWN store only
- receive orders (own store's orders only)
- update order status along the allowed path
"""

from app.extensions import db
from app.models.store import Store

FIXED_CODE = "424242"


def _store_payload(**over):
    payload = {
        "name": "New Vendor Store",
        "description": "Fresh produce",
        "location": "Zahle",
        "contact_info": "vendor@example.com",
        "inside_city_delivery_fee": 2,
        "outside_city_delivery_fee": 5,
    }
    payload.update(over)
    return payload


def test_vendor_can_register(client, monkeypatch):
    monkeypatch.setattr(
        "app.services.two_factor_service._generate_verification_code",
        lambda: FIXED_CODE,
    )
    reg = client.post(
        "/api/auth/register",
        json={
            "first_name": "Omar",
            "last_name": "Baroudi",
            "email": "omar@example.com",
            "phone": "+961 3 333333",
            "password": "Passw0rd!",
            "verification_method": "email",
            "role": "vendor",
        },
    )
    assert reg.status_code == 201

    verify = client.post(
        "/api/auth/register/verify",
        json={
            "challenge_token": reg.get_json()["challenge_token"],
            "code": FIXED_CODE,
        },
    )
    assert verify.status_code == 200
    assert verify.get_json()["user"]["role"] == "vendor"


def test_vendor_can_create_store(client, auth, vendor):
    resp = client.post(
        "/api/stores", json=_store_payload(), headers=auth(vendor)
    )

    assert resp.status_code == 201
    assert resp.get_json()["store"]["name"] == "New Vendor Store"


def test_new_store_starts_pending_and_is_invisible_to_customers(
    client, auth, vendor, customer
):
    created = client.post(
        "/api/stores", json=_store_payload(), headers=auth(vendor)
    )
    store_id = created.get_json()["store"]["id"]
    assert created.get_json()["store"]["approval_status"] == "pending"

    # not in the public directory
    listing = client.get("/api/stores")
    assert all(
        s["id"] != store_id for s in listing.get_json()["stores"]
    )

    # not reachable directly
    assert client.get(f"/api/stores/{store_id}").status_code == 404


def test_vendor_can_add_product_to_own_store(
    client, auth, vendor, make_store, category
):
    store = make_store(owner=vendor, approval_status="pending")

    resp = client.post(
        "/api/products",
        json={
            "name": "Merwah White",
            "description": "Bekaa white wine",
            "price": 18.0,
            "stock": 12,
            "store_id": store.id,
            "category_id": category.id,
        },
        headers=auth(vendor),
    )

    assert resp.status_code == 201


def test_vendor_cannot_add_product_to_another_vendors_store(
    client, auth, make_user, make_store, category
):
    owner = make_user("vendor", email="owner-v@test.local")
    intruder = make_user("vendor", email="intruder-v@test.local")
    store = make_store(owner=owner)

    resp = client.post(
        "/api/products",
        json={
            "name": "Sneaky Product",
            "price": 5.0,
            "stock": 1,
            "store_id": store.id,
            "category_id": category.id,
        },
        headers=auth(intruder),
    )

    assert resp.status_code == 403


def test_vendor_edits_own_product(client, auth, vendor, make_store, make_product):
    store = make_store(owner=vendor)
    product = make_product(store=store, price=10.0)

    resp = client.put(
        f"/api/products/{product.id}",
        json={"price": 12.5},
        headers=auth(vendor),
    )

    assert resp.status_code == 200
    db.session.expire_all()
    from app.models.product import Product

    assert float(db.session.get(Product, product.id).price) == 12.5


def test_vendor_sees_only_own_incoming_orders(
    client, auth, make_user, make_store, make_product, make_order
):
    v1 = make_user("vendor", email="v1@test.local")
    v2 = make_user("vendor", email="v2@test.local")
    s1 = make_store(owner=v1)
    s2 = make_store(owner=v2)
    make_order(product=make_product(store=s1))
    make_order(product=make_product(store=s1))
    make_order(product=make_product(store=s2))

    resp = client.get("/api/vendor/orders", headers=auth(v1))

    assert resp.status_code == 200
    orders = resp.get_json()["orders"]
    assert len(orders) == 2
    assert all(o["store_id"] == s1.id for o in orders)


def test_vendor_advances_order_pending_processing_delivered(
    client, auth, vendor, make_store, make_product, make_order
):
    store = make_store(owner=vendor)
    order = make_order(product=make_product(store=store), status="pending")

    to_processing = client.patch(
        f"/api/orders/{order.id}/status",
        json={"status": "processing"},
        headers=auth(vendor),
    )
    assert to_processing.status_code == 200
    assert to_processing.get_json()["order"]["status"] == "processing"

    to_delivered = client.patch(
        f"/api/orders/{order.id}/status",
        json={"status": "delivered"},
        headers=auth(vendor),
    )
    assert to_delivered.status_code == 200
    assert to_delivered.get_json()["order"]["status"] == "delivered"


def test_vendor_invalid_status_transition_is_rejected(
    client, auth, vendor, make_store, make_product, make_order
):
    store = make_store(owner=vendor)
    order = make_order(product=make_product(store=store), status="pending")

    # pending -> delivered skips a step
    resp = client.patch(
        f"/api/orders/{order.id}/status",
        json={"status": "delivered"},
        headers=auth(vendor),
    )

    assert resp.status_code == 400
    db.session.expire_all()
    from app.models.order import Order

    assert db.session.get(Order, order.id).status == "pending"


def test_vendor_manages_store_information(client, auth, vendor, make_store):
    store = make_store(owner=vendor, location="Beirut")

    resp = client.put(
        f"/api/stores/{store.id}",
        json={"location": "Jounieh", "description": "Moved to Jounieh"},
        headers=auth(vendor),
    )

    assert resp.status_code == 200
    db.session.expire_all()
    assert db.session.get(Store, store.id).location == "Jounieh"
