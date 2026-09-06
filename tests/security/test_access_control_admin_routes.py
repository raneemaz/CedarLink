"""A01 — every admin-only route refuses a customer and a vendor.

The admin surface is not one blueprint: ``admin_bp`` and ``admin_coupons``
sit under ``/api/admin/``, the review-moderation routes are registered
there too, and the category write routes are admin-only while living at
``/api/categories``. All of them are enumerated from ``app.url_map`` here.

``test_every_admin_prefixed_route_is_covered`` is the rot guard: any new
``/api/admin/...`` route that is not in ``ADMIN_ROUTES`` fails the suite
until it is added (and therefore probed).
"""

import re

import pytest

# endpoint -> (methods, body for a mutating probe)
ADMIN_ROUTES = {
    "admin.get_all_users": (["GET"], None),
    "admin.suspend_user": (["PATCH"], {"reason": "x"}),
    "admin.unsuspend_user": (["PATCH"], None),
    "admin.get_all_stores": (["GET"], None),
    "admin.delete_store": (["DELETE"], None),
    "admin.approve_store": (["PATCH"], None),
    "admin.reject_store": (["PATCH"], {"note": "x"}),
    "admin.get_reports": (["GET"], None),
    "admin_coupons.admin_list_coupons": (["GET"], None),
    "admin_coupons.admin_create_coupon": (
        ["POST"],
        {"code": "X", "discount_type": "percentage", "value": 10},
    ),
    "admin_coupons.admin_update_coupon": (["PUT"], {"value": 5}),
    "admin_coupons.admin_delete_coupon": (["DELETE"], None),
    "review_bp.admin_list_reviews": (["GET"], None),
    "review_bp.admin_moderate_review": (["PATCH"], {"status": "removed"}),
    # Admin-only but not under /api/admin/ — hand-listed on purpose.
    "category_bp.create_category": (
        ["POST"], {"name_en": "X", "description": "x"}
    ),
    "category_bp.update_category": (["PUT"], {"name_en": "X"}),
    "category_bp.delete_category": (["DELETE"], None),
}


def _fill(rule):
    return re.sub(r"<[^>]+>", "1", str(rule))


@pytest.fixture()
def rules_by_endpoint(app):
    return {r.endpoint: r for r in app.url_map.iter_rules()}


@pytest.mark.parametrize("as_role", ["customer", "vendor"])
def test_admin_routes_refuse_non_admins(
    app, client, auth, make_user, rules_by_endpoint, as_role
):
    caller = make_user(as_role, email=f"{as_role}@adminprobe.local")
    headers = auth(caller)
    failures = []

    for endpoint, (methods, body) in ADMIN_ROUTES.items():
        rule = rules_by_endpoint[endpoint]
        path = _fill(rule)
        for method in methods:
            resp = client.open(
                path, method=method, headers=headers, json=body or {}
            )
            if resp.status_code != 403:
                failures.append(
                    f"{as_role}: {method} {path} -> {resp.status_code} "
                    f"(expected 403)"
                )

    assert not failures, "admin route reachable by non-admin:\n" + "\n".join(
        failures
    )


def test_admin_routes_refuse_anonymous(app, client, rules_by_endpoint):
    failures = []
    for endpoint, (methods, body) in ADMIN_ROUTES.items():
        path = _fill(rules_by_endpoint[endpoint])
        for method in methods:
            resp = client.open(path, method=method, json=body or {})
            if resp.status_code not in (401, 422):
                failures.append(f"{method} {path} -> {resp.status_code}")
    assert not failures, "admin route reachable without a token:\n" + "\n".join(
        failures
    )


def test_an_admin_is_actually_allowed(app, client, auth, admin,
                                      rules_by_endpoint):
    """Control: the 403s above are the role check, not a broken route."""
    path = _fill(rules_by_endpoint["admin.get_reports"])
    resp = client.get(path, headers=auth(admin))
    assert resp.status_code == 200


def test_every_admin_prefixed_route_is_covered(app):
    """Rot guard — a new /api/admin/... route must be added to ADMIN_ROUTES."""
    missing = []
    for rule in app.url_map.iter_rules():
        if str(rule.rule).startswith("/api/admin/"):
            if rule.endpoint not in ADMIN_ROUTES:
                missing.append(f"{rule.endpoint}  {rule.rule}")
    assert not missing, (
        "admin-prefixed routes not covered by this test:\n" + "\n".join(missing)
    )
