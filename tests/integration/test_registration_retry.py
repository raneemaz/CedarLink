"""Re-registering an address that was never verified (CL-10 follow-up).

An unverified user row used to block its address permanently: every retry
hit the account-enumeration decoy, which returns a convincing 201 but
creates no challenge and sends no email, so no code could ever verify.
A user who closed the tab before typing the code was locked out for good.

The decoy still stands for accounts that really exist. These tests pin
both halves: an abandoned signup can be restarted, and a verified account
cannot be probed for -- or hijacked -- by registering over it.
"""

from app.extensions import db
from app.models.user import User

FIXED_CODE = "424242"


def _payload(**over):
    body = {
        "first_name": "Nadia",
        "last_name": "Khoury",
        "email": "abandoned@example.com",
        "phone": "+961 3 111111",
        "password": "Passw0rd!",
        "verification_method": "email",
    }
    body.update(over)
    return body


def _fixed_code(monkeypatch):
    monkeypatch.setattr(
        "app.services.two_factor_service._generate_verification_code",
        lambda: FIXED_CODE,
    )


def test_an_abandoned_signup_can_register_again(client, monkeypatch):
    _fixed_code(monkeypatch)

    first = client.post("/api/auth/register", json=_payload())
    assert first.status_code == 201
    # ...and the code is never entered. The tab is closed.

    second = client.post("/api/auth/register", json=_payload())
    assert second.status_code == 201

    # The second challenge must be real, not the decoy: it verifies.
    verify = client.post(
        "/api/auth/register/verify",
        json={
            "challenge_token": second.get_json()["challenge_token"],
            "code": FIXED_CODE,
        },
    )
    assert verify.status_code == 200, verify.get_json()
    assert verify.get_json()["user"]["email"] == "abandoned@example.com"

    # One account, not two.
    assert User.query.filter_by(email="abandoned@example.com").count() == 1


def test_the_retry_takes_the_details_typed_the_second_time(
    client, monkeypatch
):
    _fixed_code(monkeypatch)

    client.post("/api/auth/register", json=_payload(first_name="Old"))
    client.post(
        "/api/auth/register",
        json=_payload(first_name="New", password="Different1!"),
    )

    user = User.query.filter_by(email="abandoned@example.com").one()
    assert user.first_name == "New"

    # The newer password is the one that works.
    client.post(
        "/api/auth/register/verify",
        json={
            "challenge_token": client.post(
                "/api/auth/register", json=_payload(password="Different1!")
            ).get_json()["challenge_token"],
            "code": FIXED_CODE,
        },
    )
    login = client.post(
        "/api/auth/login",
        json={"email": "abandoned@example.com", "password": "Different1!"},
    )
    assert login.status_code == 202


def test_a_verified_account_still_gets_the_decoy(client, monkeypatch):
    _fixed_code(monkeypatch)

    created = client.post("/api/auth/register", json=_payload())
    client.post(
        "/api/auth/register/verify",
        json={
            "challenge_token": created.get_json()["challenge_token"],
            "code": FIXED_CODE,
        },
    )

    user = User.query.filter_by(email="abandoned@example.com").one()
    original_hash = user.password

    # Registering over a real account answers exactly as it would for a
    # fresh address -- same status, same keys -- so nothing is disclosed.
    again = client.post(
        "/api/auth/register", json=_payload(password="Attacker1!")
    )
    assert again.status_code == 201
    assert set(again.get_json()) == set(created.get_json())

    # But the challenge is a decoy: it verifies to nothing.
    verify = client.post(
        "/api/auth/register/verify",
        json={
            "challenge_token": again.get_json()["challenge_token"],
            "code": FIXED_CODE,
        },
    )
    assert verify.status_code == 400

    # And the real account is untouched -- no password takeover.
    db.session.expire_all()
    assert User.query.filter_by(email="abandoned@example.com").one().password \
        == original_hash
