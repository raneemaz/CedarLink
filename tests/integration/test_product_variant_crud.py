"""V-2 — the vendor management endpoints for options, values and variants.

The rules that matter: only the owning vendor can touch them (covered in
tests/security/test_access_control_vendor_isolation.py), a duplicate value
*combination* is refused, an option or value still used by a variant can't
be deleted, retiring a variant leaves order history alone, and a variant
that has ever been ordered can't be hard-deleted.

See docs/decisions/0036-variant-management-and-picker.md.
"""

from app.extensions import db
from app.models.order import Order
from app.models.order_item import OrderItem
from app.models.product_variant import ProductVariant


def _make_axis(client, auth, vendor, product, name_en, values):
    """Create an option axis and its values; return (option_id, {value_en: id})."""
    resp = client.post(
        f"/api/products/{product.id}/options",
        json={"name_en": name_en},
        headers=auth(vendor),
    )
    assert resp.status_code == 201, resp.get_json()
    option = resp.get_json()["options"][-1]

    ids = {}
    for value_en in values:
        r = client.post(
            f"/api/products/{product.id}/options/{option['id']}/values",
            json={"value_en": value_en},
            headers=auth(vendor),
        )
        assert r.status_code == 201, r.get_json()
        added = [
            o for o in r.get_json()["options"] if o["id"] == option["id"]
        ][0]
        ids = {v["value_en"]: v["id"] for v in added["values"]}
    return option["id"], ids


def _owned(make_store, make_user, make_product):
    vendor = make_user("vendor", email="variantcrud@test.local")
    store = make_store(owner=vendor)
    product = make_product(store=store, price=20.0, stock=0)
    return vendor, product


def test_vendor_builds_an_axis_a_value_and_a_variant(
    client, auth, make_store, make_user, make_product
):
    vendor, product = _owned(make_store, make_user, make_product)

    option_id, values = _make_axis(
        client, auth, vendor, product, "Colour", ["Black", "Grey"]
    )

    resp = client.post(
        f"/api/products/{product.id}/variants",
        json={
            "option_value_ids": [values["Black"]],
            "price": "25.00",
            "stock": 4,
        },
        headers=auth(vendor),
    )
    assert resp.status_code == 201, resp.get_json()
    body = resp.get_json()
    assert len(body["variants"]) == 1
    variant = body["variants"][0]
    assert variant["label_en"] == "Black"
    assert variant["price"] == 25.0
    assert variant["stock"] == 4
    assert variant["is_active"] is True


def test_duplicate_combination_is_refused(
    client, auth, make_store, make_user, make_product
):
    vendor, product = _owned(make_store, make_user, make_product)
    _, values = _make_axis(
        client, auth, vendor, product, "Size", ["1L", "2L"]
    )

    first = client.post(
        f"/api/products/{product.id}/variants",
        json={"option_value_ids": [values["1L"]], "stock": 3},
        headers=auth(vendor),
    )
    assert first.status_code == 201

    dup = client.post(
        f"/api/products/{product.id}/variants",
        json={"option_value_ids": [values["1L"]], "stock": 9},
        headers=auth(vendor),
    )
    assert dup.status_code == 409
    assert dup.get_json()["code"] == "combination_taken"


def test_incomplete_combination_is_refused(
    client, auth, make_store, make_user, make_product
):
    vendor, product = _owned(make_store, make_user, make_product)
    colour_id, colours = _make_axis(
        client, auth, vendor, product, "Colour", ["Red"]
    )
    _make_axis(client, auth, vendor, product, "Size", ["S", "M"])

    resp = client.post(
        f"/api/products/{product.id}/variants",
        json={"option_value_ids": [colours["Red"]], "stock": 1},
        headers=auth(vendor),
    )
    assert resp.status_code == 400
    assert resp.get_json()["code"] == "incomplete_combination"


def test_option_still_used_by_a_variant_cannot_be_deleted(
    client, auth, make_store, make_user, make_product
):
    vendor, product = _owned(make_store, make_user, make_product)
    option_id, values = _make_axis(
        client, auth, vendor, product, "Colour", ["Black"]
    )
    client.post(
        f"/api/products/{product.id}/variants",
        json={"option_value_ids": [values["Black"]], "stock": 2},
        headers=auth(vendor),
    )

    resp = client.delete(
        f"/api/products/{product.id}/options/{option_id}",
        headers=auth(vendor),
    )
    assert resp.status_code == 409
    assert resp.get_json()["code"] == "option_in_use"


def test_retiring_a_variant_does_not_touch_order_history(
    client, auth, make_store, make_user, make_product
):
    vendor, product = _owned(make_store, make_user, make_product)
    _, values = _make_axis(
        client, auth, vendor, product, "Colour", ["Grey"]
    )
    created = client.post(
        f"/api/products/{product.id}/variants",
        json={"option_value_ids": [values["Grey"]], "price": "25.00",
              "stock": 5},
        headers=auth(vendor),
    ).get_json()
    variant_id = created["variants"][0]["id"]

    customer = make_user("customer", email="vc-buyer@test.local")
    order = Order(
        user_id=customer.id, store_id=product.store_id, status="delivered",
        delivery_address="1 St", delivery_city="Beirut", total_price=25,
    )
    db.session.add(order)
    db.session.flush()
    db.session.add(OrderItem(
        order_id=order.id, product_id=product.id, quantity=1,
        unit_price=25, variant_id=variant_id,
        variant_label_en="Grey", variant_label_ar="رمادي",
        variant_label_fr="Gris",
    ))
    db.session.commit()

    resp = client.patch(
        f"/api/products/{product.id}/variants/{variant_id}",
        json={"is_active": False},
        headers=auth(vendor),
    )
    assert resp.status_code == 200
    assert resp.get_json()["variants"][0]["is_active"] is False

    db.session.expire_all()
    item = OrderItem.query.filter_by(order_id=order.id).one()
    assert item.variant_id == variant_id
    assert item.variant_label_en == "Grey"
    assert db.session.get(ProductVariant, variant_id) is not None


def test_an_ordered_variant_cannot_be_hard_deleted_a_fresh_one_can(
    client, auth, make_store, make_user, make_product
):
    vendor, product = _owned(make_store, make_user, make_product)
    option_id, values = _make_axis(
        client, auth, vendor, product, "Colour", ["Black", "Grey"]
    )

    ordered = client.post(
        f"/api/products/{product.id}/variants",
        json={"option_value_ids": [values["Black"]], "stock": 5},
        headers=auth(vendor),
    ).get_json()["variants"][0]
    fresh = client.post(
        f"/api/products/{product.id}/variants",
        json={"option_value_ids": [values["Grey"]], "stock": 5},
        headers=auth(vendor),
    ).get_json()["variants"][-1]

    customer = make_user("customer", email="vc-buyer2@test.local")
    order = Order(
        user_id=customer.id, store_id=product.store_id, status="pending",
        delivery_address="1 St", delivery_city="Beirut", total_price=20,
    )
    db.session.add(order)
    db.session.flush()
    db.session.add(OrderItem(
        order_id=order.id, product_id=product.id, quantity=1,
        unit_price=20, variant_id=ordered["id"], variant_label_en="Black",
    ))
    db.session.commit()

    blocked = client.delete(
        f"/api/products/{product.id}/variants/{ordered['id']}",
        headers=auth(vendor),
    )
    assert blocked.status_code == 409
    assert blocked.get_json()["code"] == "variant_ordered"

    ok = client.delete(
        f"/api/products/{product.id}/variants/{fresh['id']}",
        headers=auth(vendor),
    )
    assert ok.status_code == 200
    assert db.session.get(ProductVariant, fresh["id"]) is None


def test_a_value_from_another_product_is_rejected(
    client, auth, make_store, make_user, make_product
):
    vendor, product = _owned(make_store, make_user, make_product)
    _make_axis(client, auth, vendor, product, "Colour", ["Black"])

    other = make_product(store=product.store, price=10.0, stock=0)
    _, other_values = _make_axis(
        client, auth, vendor, other, "Colour", ["Blue"]
    )

    resp = client.post(
        f"/api/products/{product.id}/variants",
        json={"option_value_ids": [other_values["Blue"]], "stock": 1},
        headers=auth(vendor),
    )
    assert resp.status_code == 400
