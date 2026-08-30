"""CL-10 — auth endpoints must not leak account existence and must be
throttled.
"""

from app.extensions import db
from app.models.user import User


def _register_body(email, method="email"):
    return {
        "first_name": "Sam",
        "last_name": "Taken",
        "email": email,
        "phone": "+961 3 987654",
        "password": "Passw0rd!",
        "verification_method": method,
    }


# --- enumeration ------------------------------------------------------- #

def test_registration_answers_the_same_for_taken_and_free_email(
    client, make_user
):
    existing = make_user("customer", email="already@cedarlink.test")

    free = client.post(
        "/api/auth/register", json=_register_body("nobody@cedarlink.test")
    )
    taken = client.post(
        "/api/auth/register", json=_register_body(existing.email)
    )

    assert free.status_code == taken.status_code == 201
    assert free.get_json().keys() == taken.get_json().keys()
    assert free.get_json()["message"] == taken.get_json()["message"]
    assert "exist" not in taken.get_data(as_text=True).lower()


def test_registration_decoy_creates_nothing_and_leads_nowhere(
    client, make_user
):
    existing = make_user("customer", email="victim@cedarlink.test")
    original_hash = existing.password

    resp = client.post(
        "/api/auth/register", json=_register_body(existing.email)
    )
    assert resp.status_code == 201

    # No second row, existing account untouched.
    assert User.query.filter_by(email=existing.email).count() == 1
    assert db.session.get(User, existing.id).password == original_hash

    # The decoy challenge token verifies to nothing.
    verify = client.post(
        "/api/auth/register/verify",
        json={
            "challenge_token": resp.get_json()["challenge_token"],
            "code": "000000",
        },
    )
    assert verify.status_code >= 400


# --- throttling ------------------------------------------------------- #

def test_login_is_rate_limited_per_account(client, make_user, rate_limiting):
    user = make_user("customer", email="target@cedarlink.test")

    statuses = [
        client.post(
            "/api/auth/login",
            json={"email": user.email, "password": "wrong-password"},
        ).status_code
        for _ in range(7)
    ]

    assert statuses[0] == 401
    assert 429 in statuses


def test_registration_is_rate_limited_per_ip(client, rate_limiting):
    statuses = [
        client.post(
            "/api/auth/register",
            json=_register_body(f"flood{i}@cedarlink.test"),
        ).status_code
        for i in range(8)
    ]

    assert statuses[0] == 201
    assert 429 in statuses
