"""ADR 0033 §5 item 4 — security response headers.

A small set for a JSON API, added in an `after_request` hook. HSTS is
stamped only when the request already arrived over TLS (honouring the
proxy's `X-Forwarded-Proto` via ProxyFix), so it is inert in local dev
and correct in production. CSP is intentionally absent — see the ADR.
"""

import pytest

STATIC_HEADERS = {
    "X-Content-Type-Options": "nosniff",
    "X-Frame-Options": "DENY",
    "Referrer-Policy": "strict-origin-when-cross-origin",
}


@pytest.mark.parametrize("path", ["/api/products", "/api/exchange-rates"])
def test_static_security_headers_on_every_response(client, path):
    resp = client.get(path)
    for name, value in STATIC_HEADERS.items():
        assert resp.headers.get(name) == value, name


def test_headers_are_present_on_an_error_response_too(client):
    resp = client.get("/api/orders")  # 401, no token
    assert resp.status_code == 401
    assert resp.headers.get("X-Content-Type-Options") == "nosniff"


def test_hsts_is_absent_over_plain_http(client):
    resp = client.get("/api/products")
    assert "Strict-Transport-Security" not in resp.headers


def test_hsts_is_present_when_the_request_is_https(client):
    resp = client.get(
        "/api/products", headers={"X-Forwarded-Proto": "https"}
    )
    hsts = resp.headers.get("Strict-Transport-Security")
    assert hsts and "max-age=31536000" in hsts
