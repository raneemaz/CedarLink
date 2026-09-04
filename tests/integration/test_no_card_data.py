"""No card number reaches the server, and none is stored.

CedarLink used to accept a full PAN and keep an unsalted SHA-256 of it.
A card number is low-entropy — a known BIN plus a Luhn check digit leaves
about a billion candidates — so that digest was the card number with an
extra step. See docs/decisions/0024-no-card-data.md.

The property these tests hold down is not "the hash is gone" but "the
number never arrives": the endpoint refuses any request carrying one, so
there is nothing to leak from a log, a traceback or a backup.
"""

import pytest
from sqlalchemy import inspect, text

from app.extensions import db
from app.models.payment_method import PaymentMethod
from app.routes.payment_method_routes import FORBIDDEN_FIELDS

URL = "/api/payment-methods"

# A real-format test PAN (Visa test range, passes Luhn). Never a real card.
TEST_PAN = "4242424242424242"

VALID = {
    "type": "card",
    "label": "R. Abou Zeid",
    "brand": "Visa",
    "last4": "4242",
    "exp_month": 11,
    "exp_year": 2030,
}


def _create(client, auth, customer, **overrides):
    return client.post(
        URL, json={**VALID, **overrides}, headers=auth(customer)
    )


# --------------------------------------------------------------------------- #
# The number never arrives
# --------------------------------------------------------------------------- #

@pytest.mark.parametrize("field", FORBIDDEN_FIELDS)
def test_every_pan_or_cvv_field_is_refused(
    client, auth, customer, field
):
    """Refused, not ignored.

    Silently dropping the field would let an old client keep putting a
    card number on the wire believing it was handled — and the wire is
    the part that matters.
    """
    response = _create(client, auth, customer, **{field: TEST_PAN})

    assert response.status_code == 400, (
        f"{field!r} was accepted; the endpoint must refuse it"
    )
    assert field in response.get_json()["message"]
    assert PaymentMethod.query.count() == 0


def test_a_refused_request_persists_nothing(client, auth, customer):
    response = _create(client, auth, customer, card_number=TEST_PAN)

    assert response.status_code == 400
    assert PaymentMethod.query.count() == 0


def test_the_pan_appears_nowhere_in_the_database(client, auth, customer):
    """Sweep every text column of every table for the digits."""
    _create(client, auth, customer, card_number=TEST_PAN)   # refused
    assert _create(client, auth, customer).status_code == 201  # accepted

    inspector = inspect(db.engine)
    hits = []

    for table in inspector.get_table_names():
        columns = [c["name"] for c in inspector.get_columns(table)]
        for column in columns:
            rows = db.session.execute(
                text(
                    f'SELECT COUNT(*) FROM "{table}" '
                    f'WHERE CAST("{column}" AS TEXT) LIKE :needle'
                ),
                {"needle": f"%{TEST_PAN}%"},
            ).scalar()
            if rows:
                hits.append(f"{table}.{column}")

    assert hits == [], f"the card number was stored in {hits}"


def test_no_column_holds_anything_derived_from_a_card_number(client):
    """The hash column is gone, and nothing replaced it.

    Named columns rather than a blanket check, so adding a legitimate
    column never fails this test but re-adding a digest of the PAN does.
    """
    columns = {c["name"] for c in inspect(db.engine).get_columns(
        "payment_methods"
    )}

    for banned in ("number_hash", "card_number", "pan", "number",
                   "cvv", "cvc", "security_code"):
        assert banned not in columns, (
            f"payment_methods.{banned} is back — see ADR 0024"
        )


# --------------------------------------------------------------------------- #
# What the endpoint does accept
# --------------------------------------------------------------------------- #

def test_a_card_is_saved_from_brand_last4_expiry_and_holder(
    client, auth, customer
):
    response = _create(client, auth, customer)
    assert response.status_code == 201

    saved = response.get_json()["payment_method"]
    assert saved["brand"] == "Visa"
    assert saved["last4"] == "4242"
    assert saved["exp_month"] == 11
    assert saved["exp_year"] == 2030
    assert saved["label"] == "R. Abou Zeid"
    assert "number_hash" not in saved

    row = PaymentMethod.query.one()
    assert row.last4 == "4242"
    assert not hasattr(row, "number_hash")


@pytest.mark.parametrize(
    "last4, expected",
    [
        ("42", "four digits"),
        ("42424", "four digits"),
        ("abcd", "four digits"),
        ("", "required"),
        (None, "required"),
    ],
)
def test_last_four_must_be_exactly_four_digits(
    client, auth, customer, last4, expected
):
    response = _create(client, auth, customer, last4=last4)
    assert response.status_code == 400
    assert expected in response.get_json()["message"]


def test_a_full_pan_in_the_last4_field_is_refused(client, auth, customer):
    """The obvious way to smuggle the number past a last-four field."""
    response = _create(client, auth, customer, last4=TEST_PAN)

    assert response.status_code == 400
    assert PaymentMethod.query.count() == 0


@pytest.mark.parametrize(
    "month, year, expected",
    [
        (0, 2030, "between 1 and 12"),
        (13, 2030, "between 1 and 12"),
        (11, 30, "four-digit year"),
        (1, 2020, "expired"),
        (None, 2030, "required"),
        (11, None, "required"),
    ],
)
def test_expiry_is_validated(
    client, auth, customer, month, year, expected
):
    response = _create(
        client, auth, customer, exp_month=month, exp_year=year
    )
    assert response.status_code == 400
    assert expected in response.get_json()["message"]


def test_updating_a_card_also_refuses_a_card_number(
    client, auth, customer
):
    card_id = _create(client, auth, customer).get_json()[
        "payment_method"
    ]["id"]

    response = client.put(
        f"{URL}/{card_id}",
        json={**VALID, "card_number": TEST_PAN},
        headers=auth(customer),
    )
    assert response.status_code == 400
    assert "card_number" in response.get_json()["message"]


def test_updating_a_card_changes_last_four_and_expiry(
    client, auth, customer
):
    card_id = _create(client, auth, customer).get_json()[
        "payment_method"
    ]["id"]

    response = client.put(
        f"{URL}/{card_id}",
        json={**VALID, "last4": "1881", "exp_month": 3, "exp_year": 2031},
        headers=auth(customer),
    )
    assert response.status_code == 200

    updated = response.get_json()["payment_method"]
    assert updated["last4"] == "1881"
    assert updated["exp_month"] == 3
    assert updated["exp_year"] == 2031
