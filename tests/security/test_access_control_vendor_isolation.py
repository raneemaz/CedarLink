"""A01 — a vendor cannot read or write another store's data.

Store-scoped routes go through ``_load_owned_store`` (403 on a foreign
store); product routes check ``product.store.owner_id``; the three
``/api/vendor/*`` routes are self-scoped by the token and cannot even name
another store, so those are checked for *data* isolation instead.

``test_every_store_and_vendor_route_is_classified`` is the rot guard: a new
``/api/stores/<int:store_id>/...`` mutation or ``/api/vendor/...`` route
that is not listed here fails the suite until it is.
"""

import re

import pytest

# Store-scoped routes that MUST refuse a non-owner vendor.
# endpoint -> (method, body)
FOREIGN_STORE_ROUTES = {
    "store.update_store": ("PUT", {"name": "x"}),
    "store.set_store_hours": ("PUT", {"hours": []}),
    "store.set_store_location": ("PUT", {"latitude": 33.9, "longitude": 35.5}),
    "store.set_store_override": ("PATCH", {"status": "closed"}),
    "store.clear_store_override": ("DELETE", None),
    "store.toggle_store_status": ("PATCH", {"is_active": False}),
    "store.create_store_announcement": (
        "POST", {"title": "x", "body": "x", "starts_at": "2026-01-01"}
    ),
    "store.update_store_announcement": ("PUT", {"title": "x"}),
    "store.delete_store_announcement": ("DELETE", None),
    "store.set_store_social_links": ("PUT", {"links": []}),
    "store.preview_store_social_links": ("POST", {"links": []}),
    "vendor_coupons.list_store_coupons": ("GET", None),
    "vendor_coupons.create_store_coupon": (
        "POST", {"code": "X", "discount_type": "percentage", "value": 10}
    ),
    "vendor_coupons.update_store_coupon": ("PUT", {"value": 5}),
    "vendor_coupons.delete_store_coupon": ("DELETE", None),
}

# Product-scoped routes that MUST refuse a vendor who does not own the store.
FOREIGN_PRODUCT_ROUTES = {
    "product_bp.update_product": ("PUT", {"price": 1}),
    "product_bp.delete_product": ("DELETE", None),
    "product_image_bp.add_image": ("POST", None),
    "product_image_bp.delete_image": ("DELETE", None),
    # V-2 option / value / variant CRUD — the ownership check fires before
    # any sub-resource lookup, so the sub-ids here are placeholders.
    "product_variant_bp.create_option": ("POST", {"name_en": "x"}),
    "product_variant_bp.update_option": ("PUT", {"name_en": "x"}),
    "product_variant_bp.delete_option": ("DELETE", None),
    "product_variant_bp.create_value": ("POST", {"value_en": "x"}),
    "product_variant_bp.update_value": ("PUT", {"value_en": "x"}),
    "product_variant_bp.delete_value": ("DELETE", None),
    "product_variant_bp.create_variant": ("POST", {"stock": 1}),
    "product_variant_bp.update_variant": ("PUT", {"stock": 1}),
    "product_variant_bp.set_variant_active": ("PATCH", {"is_active": False}),
    "product_variant_bp.delete_variant": ("DELETE", None),
}

# Public reads on a store — not an isolation boundary, excluded on purpose.
PUBLIC_STORE_READS = {
    "store.get_store", "store.get_store_hours", "store.get_store_announcements",
    "store.get_store_social_links", "review_bp.get_store_reviews",
}


@pytest.fixture()
def two_vendors(make_store, make_product, make_user, make_order):
    from app.extensions import db
    from app.models.coupon import Coupon
    from app.models.store_announcement import StoreAnnouncement
    from app.models.store_social_link import StoreSocialLink

    victim = make_user("vendor", email="victim-vendor@iso.local")
    store = make_store(owner=victim, name="Victim Store")
    product = make_product(store=store, stock=5)
    customer = make_user("customer", email="buyer@iso.local")
    order = make_order(customer=customer, product=product, status="pending")
    coupon = Coupon(
        code="VICT", discount_type="percentage", value=10, is_active=True,
        store_id=store.id,
    )
    ann = StoreAnnouncement(
        store_id=store.id, title="V", body="v", starts_at=_naive(),
    )
    link = StoreSocialLink(
        store_id=store.id, platform="instagram", value="https://x/y",
    )
    db.session.add_all([coupon, ann, link])
    db.session.commit()

    attacker = make_user("vendor", email="attacker-vendor@iso.local")
    make_store(owner=attacker, name="Attacker Store")

    return {
        "attacker": attacker,
        "store_id": store.id,
        "product_id": product.id,
        "order_id": order.id,
        "coupon_id": coupon.id,
        "announcement_id": ann.id,
        "image_id": 1,
    }


def _naive():
    from datetime import datetime, timezone
    return datetime.now(timezone.utc).replace(tzinfo=None)


def _fill(rule, ctx):
    out = str(rule)
    out = out.replace("<int:store_id>", str(ctx["store_id"]))
    out = out.replace("<int:id>", str(ctx["product_id"]))
    out = out.replace("<int:product_id>", str(ctx["product_id"]))
    out = out.replace("<int:coupon_id>", str(ctx["coupon_id"]))
    out = out.replace("<int:aid>", str(ctx["announcement_id"]))
    out = out.replace("<int:image_id>", str(ctx["image_id"]))
    # V-2 variant sub-resources — placeholders; ownership is checked first.
    out = out.replace("<int:option_id>", "1")
    out = out.replace("<int:value_id>", "1")
    out = out.replace("<int:variant_id>", "1")
    return out


def test_a_vendor_cannot_touch_another_store(
    app, client, auth, two_vendors
):
    headers = auth(two_vendors["attacker"])
    rules = {r.endpoint: r for r in app.url_map.iter_rules()}
    failures = []

    for endpoint, (method, body) in {
        **FOREIGN_STORE_ROUTES, **FOREIGN_PRODUCT_ROUTES
    }.items():
        path = _fill(rules[endpoint].rule, two_vendors)
        resp = client.open(path, method=method, headers=headers, json=body or {})
        if resp.status_code not in (403, 404):
            failures.append(
                f"{method} {path} ({endpoint}) -> {resp.status_code} "
                f"body={resp.get_data(as_text=True)[:120]}"
            )

    assert not failures, "vendor crossed a store boundary:\n" + "\n".join(
        failures
    )


def test_the_owner_is_still_allowed(app, client, auth, make_store, make_user):
    """Control: the 403s are ownership, not a dead route."""
    owner = make_user("vendor", email="owner-vendor@iso.local")
    store = make_store(owner=owner)
    resp = client.put(
        f"/api/stores/{store.id}",
        headers=auth(owner),
        json={"name": "Renamed", "description": "d", "location": "Beirut",
              "contact_info": "c@x.local", "inside_city_delivery_fee": 1,
              "outside_city_delivery_fee": 2},
    )
    assert resp.status_code == 200


def test_vendor_dashboard_and_store_are_self_scoped(
    app, client, auth, two_vendors
):
    """The attacker's /api/vendor/* shows the attacker's own store, never
    the victim's — there is no id to tamper with, so this checks the data."""
    headers = auth(two_vendors["attacker"])

    store_resp = client.get("/api/vendor/store", headers=headers)
    assert store_resp.status_code == 200
    assert store_resp.get_json()["store"]["id"] != two_vendors["store_id"]

    dash = client.get("/api/vendor/dashboard", headers=headers)
    assert dash.status_code == 200
    # The attacker's store has no orders; the victim's has one.
    assert dash.get_json().get("totals", {}).get("orders", 0) == 0


@pytest.mark.parametrize("as_role", ["customer"])
def test_vendor_routes_refuse_a_customer(app, client, auth, make_user, as_role):
    caller = make_user(as_role, email=f"{as_role}@vendorprobe.local")
    headers = auth(caller)
    for path in ("/api/vendor/store", "/api/vendor/dashboard",
                 "/api/vendor/orders"):
        assert client.get(path, headers=headers).status_code == 403, path


def test_every_store_and_vendor_route_is_classified(app):
    classified = (
        set(FOREIGN_STORE_ROUTES) | set(FOREIGN_PRODUCT_ROUTES)
        | PUBLIC_STORE_READS
        | {"vendor.get_my_store", "vendor.get_my_dashboard",
           "order_bp.get_vendor_orders", "store.create_store",
           "store.get_stores"}
    )
    missing = []
    for rule in app.url_map.iter_rules():
        path = str(rule.rule)
        is_store_scoped = bool(re.match(r"^/api/stores/<int:store_id>", path))
        is_vendor = path.startswith("/api/vendor/")
        if (is_store_scoped or is_vendor) and rule.endpoint not in classified:
            missing.append(f"{rule.endpoint}  {path}")
    assert not missing, (
        "store/vendor routes not classified for isolation testing:\n"
        + "\n".join(missing)
    )
