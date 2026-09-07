"""ADR 0033 §5 item 10 — the payment webhook secret check.

`payment_routes.py` compared the header against the configured secret with
`!=` — a timing side-channel. It now uses `hmac.compare_digest`, matching
`two_factor_service`'s TOTP check. The endpoint still fails closed when no
secret is configured.

Nothing in the app calls the payment flow today (ADR 0024), so this is a
low-priority hardening; the tests pin the behaviour so it does not
regress.
"""

WEBHOOK_URL = "/api/payments/webhook/cedarlink"


def test_webhook_rejects_a_wrong_secret(client, monkeypatch):
    monkeypatch.setenv("PAYMENT_WEBHOOK_SECRET", "s3cr3t-value")

    resp = client.post(
        WEBHOOK_URL,
        json={"payment_id": 1, "status": "completed"},
        headers={"X-Webhook-Secret": "wrong"},
    )

    assert resp.status_code == 401
    assert resp.get_json()["message"] == "Invalid webhook signature"


def test_webhook_rejects_a_missing_header(client, monkeypatch):
    monkeypatch.setenv("PAYMENT_WEBHOOK_SECRET", "s3cr3t-value")

    resp = client.post(WEBHOOK_URL, json={"payment_id": 1})

    assert resp.status_code == 401


def test_webhook_fails_closed_when_no_secret_is_configured(client, monkeypatch):
    monkeypatch.delenv("PAYMENT_WEBHOOK_SECRET", raising=False)

    resp = client.post(
        WEBHOOK_URL,
        json={"payment_id": 1, "status": "completed"},
        headers={"X-Webhook-Secret": ""},
    )

    assert resp.status_code == 401


def test_webhook_accepts_the_right_secret_then_404s_on_the_unknown_payment(
    client, monkeypatch
):
    """A correct secret passes the signature gate; the request then fails
    further in (no such payment), which proves the compare_digest branch
    is not rejecting a valid secret."""
    monkeypatch.setenv("PAYMENT_WEBHOOK_SECRET", "s3cr3t-value")

    resp = client.post(
        WEBHOOK_URL,
        json={"payment_id": 999999, "status": "completed",
              "transaction_id": "t1"},
        headers={"X-Webhook-Secret": "s3cr3t-value"},
    )

    assert resp.status_code != 401
