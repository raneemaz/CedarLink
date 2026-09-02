"""Admin user stories from CedarLink.md (and responsibilities: approvals,
suspensions, category management).
"""

import pytest

from app.extensions import db
from app.models.order import Order


def test_admin_lists_all_users(client, auth, admin, make_user):
    make_user("customer")
    make_user("vendor")

    resp = client.get("/api/admin/users", headers=auth(admin))

    assert resp.status_code == 200
    roles = {u["role"] for u in resp.get_json()}
    assert {"admin", "customer", "vendor"} <= roles


def test_admin_lists_all_stores(client, auth, admin, make_store):
    make_store(name="Store One")
    make_store(name="Store Two", approval_status="pending")

    resp = client.get("/api/admin/stores", headers=auth(admin))

    assert resp.status_code == 200
    names = {s["name"] for s in resp.get_json()}
    assert {"Store One", "Store Two"} <= names


def test_approving_pending_store_makes_it_visible(
    client, auth, admin, make_store
):
    store = make_store(approval_status="pending")
    assert client.get(f"/api/stores/{store.id}").status_code == 404

    resp = client.patch(
        f"/api/admin/stores/{store.id}/approve",
        json={"note": "looks good"},
        headers=auth(admin),
    )
    assert resp.status_code == 200

    assert client.get(f"/api/stores/{store.id}").status_code == 200


def test_rejecting_store_hides_it(client, auth, admin, make_store):
    store = make_store(approval_status="approved")
    assert client.get(f"/api/stores/{store.id}").status_code == 200

    resp = client.patch(
        f"/api/admin/stores/{store.id}/reject",
        json={"note": "policy violation"},
        headers=auth(admin),
    )
    assert resp.status_code == 200

    assert client.get(f"/api/stores/{store.id}").status_code == 404


def test_approval_note_never_reaches_the_public_storefront(
    client, auth, admin, make_store
):
    """approval_note is admin-authored — the storefront must not carry it,
    but the owner and admin must (CLAUDE.md: allowlist, not dump)."""
    store = make_store(approval_status="approved")
    client.patch(
        f"/api/admin/stores/{store.id}/approve",
        json={"note": "verified the business licence"},
        headers=auth(admin),
    )

    # Public detail and directory — no approval_note.
    detail = client.get(f"/api/stores/{store.id}").get_json()["store"]
    assert "approval_note" not in detail
    listed = client.get("/api/stores").get_json()["stores"][0]
    assert "approval_note" not in listed

    # Owner's own view — approval_note present.
    mine = client.get(
        "/api/vendor/store", headers=auth(store.owner)
    ).get_json()["store"]
    assert mine["approval_note"] == "verified the business licence"

    # Admin list — present.
    admin_row = next(
        s for s in client.get(
            "/api/admin/stores", headers=auth(admin)
        ).get_json()
        if s["id"] == store.id
    )
    assert admin_row["approval_note"] == "verified the business licence"


def test_suspending_user_blocks_their_login(
    client, auth, admin, make_user
):
    victim = make_user("customer", email="victim@test.local")
    assert (
        client.post(
            "/api/auth/login",
            json={"email": victim.email, "password": victim.plain_password},
        ).status_code
        == 202
    )

    client.patch(
        f"/api/admin/users/{victim.id}/suspend",
        json={"reason": "spam"},
        headers=auth(admin),
    )

    blocked = client.post(
        "/api/auth/login",
        json={"email": victim.email, "password": victim.plain_password},
    )
    assert blocked.status_code == 403
    assert blocked.get_json()["account_suspended"] is True


def test_suspending_user_blocks_their_reactivate(
    client, auth, admin, make_user
):
    victim = make_user("customer", email="victim2@test.local")
    client.patch(
        f"/api/admin/users/{victim.id}/suspend",
        json={},
        headers=auth(admin),
    )

    resp = client.post(
        "/api/auth/reactivate",
        json={"email": victim.email, "password": victim.plain_password},
    )
    assert resp.status_code == 403


def test_removing_store_hides_products_but_preserves_orders(
    client, auth, admin, customer, make_store, make_product, make_order
):
    store = make_store()
    product = make_product(store=store, name="Doomed", stock=5)
    order = make_order(customer=customer, product=product, quantity=2)

    remove = client.delete(
        f"/api/admin/stores/{store.id}", headers=auth(admin)
    )
    assert remove.status_code == 200

    # gone from the storefront
    listing = client.get("/api/products").get_json()
    assert all(p["id"] != product.id for p in listing["products"])
    assert client.get(f"/api/products/{product.id}").status_code == 404

    # the customer's order is untouched
    history = client.get(
        f"/api/orders/{order.id}", headers=auth(customer)
    )
    assert history.status_code == 200
    got = history.get_json()["order"]
    assert got["items"][0]["product_name"] == "Doomed"
    assert got["items"][0]["quantity"] == 2

    db.session.expire_all()
    assert db.session.get(Order, order.id) is not None


ADMIN_ENDPOINTS = [
    ("get", "/api/admin/users", None),
    ("get", "/api/admin/stores", None),
    ("get", "/api/admin/reports", None),
    ("delete", "/api/admin/stores/1", None),
    ("patch", "/api/admin/users/1/suspend", {"reason": "x"}),
    ("patch", "/api/admin/users/1/unsuspend", {}),
    ("patch", "/api/admin/stores/1/approve", {}),
    ("patch", "/api/admin/stores/1/reject", {}),
]


@pytest.mark.parametrize("method,path,body", ADMIN_ENDPOINTS)
def test_non_admin_gets_403_on_admin_endpoints(
    client, auth, customer, method, path, body
):
    resp = getattr(client, method)(
        path, json=body, headers=auth(customer)
    )
    assert resp.status_code == 403


def test_public_registration_cannot_create_an_admin(client):
    resp = client.post(
        "/api/auth/register",
        json={
            "first_name": "Mallory",
            "last_name": "Root",
            "email": "mallory@example.com",
            "phone": "+961 3 444444",
            "password": "Passw0rd!",
            "verification_method": "email",
            "role": "admin",
        },
    )
    assert resp.status_code == 400
    from app.models.user import User

    assert User.query.filter_by(email="mallory@example.com").first() is None


def test_admin_manages_categories(client, auth, admin):
    created = client.post(
        "/api/categories",
        json={"name": "Homewares", "description": "for the home"},
        headers=auth(admin),
    )
    assert created.status_code == 201
    category_id = created.get_json()["id"]

    updated = client.put(
        f"/api/categories/{category_id}",
        json={"name": "Home & Living"},
        headers=auth(admin),
    )
    assert updated.status_code == 200

    deleted = client.delete(
        f"/api/categories/{category_id}", headers=auth(admin)
    )
    assert deleted.status_code == 200
