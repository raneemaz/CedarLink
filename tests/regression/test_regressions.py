"""One test per already-fixed finding, so it stays fixed.

CL-12 — a deactivated store's products vanish from the storefront but the
        owning vendor still sees them.
CL-23 — a soft-deleted product leaves the storefront; its historical order
        line is untouched.
CL-24 — an admin-removed store keeps its orders.
"""

from app.extensions import db
from app.models.order import Order
from app.models.order_item import OrderItem
from app.models.product import Product


# --- CL-12 -------------------------------------------------------------- #

def test_cl12_inactive_store_products_hidden_from_storefront_visible_to_vendor(
    client, auth, vendor, make_store, make_product, customer
):
    store = make_store(owner=vendor, is_active=False, approval_status="approved")
    product = make_product(store=store, name="Hidden Item")

    # storefront (anonymous): gone
    anon_list = client.get("/api/products").get_json()
    assert all(p["id"] != product.id for p in anon_list["products"])
    assert client.get(f"/api/products/{product.id}").status_code == 404

    # another customer: still gone
    cust_list = client.get(
        "/api/products", headers=auth(customer)
    ).get_json()
    assert all(p["id"] != product.id for p in cust_list["products"])

    # the owning vendor: still there
    vendor_list = client.get(
        f"/api/products?store_id={store.id}", headers=auth(vendor)
    ).get_json()
    assert any(p["id"] == product.id for p in vendor_list["products"])
    assert (
        client.get(
            f"/api/products/{product.id}", headers=auth(vendor)
        ).status_code
        == 200
    )


# --- CL-23 -------------------------------------------------------------- #

def test_cl23_soft_deleted_product_gone_from_storefront_order_line_intact(
    client, auth, vendor, customer, make_store, make_product, make_order
):
    store = make_store(owner=vendor)
    product = make_product(store=store, name="Zaatar Blend", price=3.5, stock=10)
    order = make_order(customer=customer, product=product, quantity=2)

    deleted = client.delete(
        f"/api/products/{product.id}", headers=auth(vendor)
    )
    assert deleted.status_code == 200

    # storefront: gone
    listing = client.get("/api/products").get_json()
    assert all(p["id"] != product.id for p in listing["products"])
    assert client.get(f"/api/products/{product.id}").status_code == 404

    # the row still exists, just flagged
    db.session.expire_all()
    assert db.session.get(Product, product.id).deleted_at is not None

    # the order line is unchanged
    detail = client.get(
        f"/api/orders/{order.id}", headers=auth(customer)
    ).get_json()["order"]
    line = detail["items"][0]
    assert line["product_name"] == "Zaatar Blend"
    assert line["unit_price"] == 3.5
    assert line["quantity"] == 2


# --- CL-24 -------------------------------------------------------------- #

def test_cl24_removed_store_orders_preserved(
    client, auth, admin, customer, make_store, make_product, make_order
):
    store = make_store()
    product = make_product(store=store, name="Keffiyeh", price=8.0, stock=20)
    order = make_order(customer=customer, product=product, quantity=3)
    order_id = order.id

    removed = client.delete(
        f"/api/admin/stores/{store.id}", headers=auth(admin)
    )
    assert removed.status_code == 200

    # products hidden
    assert client.get(f"/api/products/{product.id}").status_code == 404

    # order + line + store row all survive
    db.session.expire_all()
    assert db.session.get(Order, order_id) is not None
    assert (
        OrderItem.query.filter_by(order_id=order_id).count() == 1
    )

    detail = client.get(
        f"/api/orders/{order_id}", headers=auth(customer)
    )
    assert detail.status_code == 200
    got = detail.get_json()["order"]
    assert got["items"][0]["product_name"] == "Keffiyeh"
    assert got["total_price"] == order.total_price
