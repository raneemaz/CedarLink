"""CL-20 — internal exception text must never reach the client, and every
blueprint speaks the same JSON error shape.

Also pins the 4b change: PUT / DELETE against a missing id return JSON, not
Werkzeug's HTML 404 page.
"""

import app.services.order_service as order_service


def _is_json(resp):
    return resp.content_type.startswith("application/json")


# --- CL-20 ------------------------------------------------------------- #

def test_checkout_500_hides_exception_text_and_returns_a_correlation_id(
    client, auth, customer, monkeypatch
):
    boom = RuntimeError(
        'null value in column "total_price" violates not-null constraint '
        'in relation "orders"'
    )

    def explode(*_args, **_kwargs):
        raise boom

    monkeypatch.setattr(order_service, "checkout", explode)

    resp = client.post(
        "/api/orders",
        json={
            "delivery_address": "1 Test Street",
            "delivery_city": "Beirut",
            "payment_method": "cash_on_delivery",
        },
        headers=auth(customer),
    )

    assert resp.status_code == 500
    assert _is_json(resp)

    body = resp.get_json()
    assert body["error"] == "An unexpected error occurred. Please try again."
    assert body["correlation_id"]

    raw = resp.get_data(as_text=True)
    assert "total_price" not in raw
    assert "not-null constraint" not in raw
    assert "orders" not in raw


def test_unknown_api_route_returns_json_not_html(client):
    resp = client.get("/api/there-is-no-such-endpoint")

    assert resp.status_code == 404
    assert _is_json(resp)
    assert "error" in resp.get_json()


# --- 4b pin: missing-id writes return JSON --------------------------- #

def test_put_missing_product_returns_json_404(client, auth, vendor):
    resp = client.put(
        "/api/products/999999",
        json={"price": 5.0},
        headers=auth(vendor),
    )

    assert resp.status_code == 404
    assert _is_json(resp)
    assert resp.get_json()["message"] == "Product not found"


def test_delete_missing_product_returns_json_404(client, auth, vendor):
    resp = client.delete("/api/products/999999", headers=auth(vendor))

    assert resp.status_code == 404
    assert _is_json(resp)
    assert resp.get_json()["message"] == "Product not found"


def test_put_missing_category_returns_json_404(client, auth, admin):
    resp = client.put(
        "/api/categories/999999",
        json={"name": "Nope"},
        headers=auth(admin),
    )

    assert resp.status_code == 404
    assert _is_json(resp)
    assert resp.get_json()["message"] == "Category not found"


def test_delete_missing_category_returns_json_404(client, auth, admin):
    resp = client.delete("/api/categories/999999", headers=auth(admin))

    assert resp.status_code == 404
    assert _is_json(resp)
    assert resp.get_json()["message"] == "Category not found"
