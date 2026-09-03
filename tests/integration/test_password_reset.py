"""Password reset (POST /api/auth/password-reset/request and /confirm).

The properties that matter on this path: it cannot be used to discover
which emails are registered, a code is single-use and short-lived, guessing
is capped, and a reset kills every session the old password was holding
open.
"""

import hashlib

import pytest

from app.extensions import db
from app.models.two_factor_challenge import TwoFactorChallenge
from app.models.user import User
from app.services import two_factor_service

REQUEST_URL = "/api/auth/password-reset/request"
CONFIRM_URL = "/api/auth/password-reset/confirm"

NEW_PASSWORD = "Brand-New-Passw0rd"


def _request(client, email):
    return client.post(REQUEST_URL, json={"email": email})


def _confirm(client, token, code, password=NEW_PASSWORD):
    return client.post(
        CONFIRM_URL,
        json={
            "challenge_token": token,
            "code": code,
            "new_password": password,
        },
    )


def _start_reset(client, sent_codes, user):
    """Request a reset and return (challenge_token, code)."""
    response = _request(client, user.email)
    assert response.status_code == 200
    return response.get_json()["challenge_token"], sent_codes.last


# --------------------------------------------------------------------------- #
# Enumeration
# --------------------------------------------------------------------------- #

def test_request_cannot_be_used_to_tell_which_emails_exist(
    client, make_user, sent_codes
):
    user = make_user("customer", email="real-account@test.local")

    real = _request(client, user.email)
    fake = _request(client, "nobody-here@test.local")

    assert real.status_code == fake.status_code == 200

    real_body, fake_body = real.get_json(), fake.get_json()
    assert real_body.keys() == fake_body.keys()
    assert real_body["message"] == fake_body["message"]
    assert real_body["method"] == fake_body["method"] == "email"
    # Both hand back a token; only one of them is backed by a challenge.
    assert real_body["challenge_token"] != fake_body["challenge_token"]

    # And the code only ever went to the account that exists.
    assert [email for email, _ in sent_codes] == [user.email]


def test_the_decoy_token_from_an_unknown_email_resets_nothing(
    client, sent_codes
):
    token = _request(client, "nobody-here@test.local").get_json()[
        "challenge_token"
    ]

    response = _confirm(client, token, "000000")
    assert response.status_code == 400
    assert TwoFactorChallenge.query.count() == 0


# --------------------------------------------------------------------------- #
# Happy path
# --------------------------------------------------------------------------- #

def test_reset_replaces_the_password_and_the_old_one_stops_working(
    client, make_user, sent_codes
):
    user = make_user("customer")
    old_password = user.plain_password
    token, code = _start_reset(client, sent_codes, user)

    assert _confirm(client, token, code).status_code == 200

    # The new password gets as far as the 2FA challenge; the old one is
    # rejected outright at the credential check.
    accepted = client.post(
        "/api/auth/login",
        json={"email": user.email, "password": NEW_PASSWORD},
    )
    assert accepted.status_code == 202

    refused = client.post(
        "/api/auth/login",
        json={"email": user.email, "password": old_password},
    )
    assert refused.status_code == 401


def test_the_reset_code_is_single_use(client, make_user, sent_codes):
    user = make_user("customer")
    token, code = _start_reset(client, sent_codes, user)

    assert _confirm(client, token, code).status_code == 200

    replay = _confirm(client, token, code, password="Another-Passw0rd")
    assert replay.status_code == 400

    # And the replay did not take effect.
    login = client.post(
        "/api/auth/login",
        json={"email": user.email, "password": "Another-Passw0rd"},
    )
    assert login.status_code == 401


def test_a_second_request_invalidates_the_first_challenge(
    client, make_user, sent_codes
):
    """_invalidate_active_challenges: only the newest code is live."""
    user = make_user("customer")
    first_token, first_code = _start_reset(client, sent_codes, user)
    second_token, second_code = _start_reset(client, sent_codes, user)

    assert first_token != second_token
    assert _confirm(client, first_token, first_code).status_code == 400
    assert _confirm(client, second_token, second_code).status_code == 200


# --------------------------------------------------------------------------- #
# Expiry, guessing and validation
# --------------------------------------------------------------------------- #

def test_an_expired_challenge_is_rejected(client, make_user, sent_codes):
    user = make_user("customer")
    token, code = _start_reset(client, sent_codes, user)

    challenge = TwoFactorChallenge.query.one()
    challenge.expires_at = two_factor_service.utcnow().replace(year=2000)
    db.session.commit()

    response = _confirm(client, token, code)
    assert response.status_code == 400
    assert "expired" in response.get_json()["message"].lower()

    # Expiry consumes the row, so a retry cannot even find it.
    db.session.refresh(challenge)
    assert challenge.consumed_at is not None


def test_a_wrong_code_is_rejected(client, make_user, sent_codes):
    user = make_user("customer")
    token, code = _start_reset(client, sent_codes, user)

    wrong = "000000" if code != "000000" else "111111"
    assert _confirm(client, token, wrong).status_code == 400

    # The real code still works — one miss does not burn the challenge.
    assert _confirm(client, token, code).status_code == 200


def test_repeated_wrong_codes_exhaust_the_challenge(
    client, app, make_user, sent_codes
):
    """The guessing cap. Without one, six digits fall in minutes."""
    cap = app.config["TWO_FACTOR_MAX_ATTEMPTS"]
    assert cap == 5

    user = make_user("customer")
    token, code = _start_reset(client, sent_codes, user)
    wrong = "000000" if code != "000000" else "111111"

    for _ in range(cap):
        assert _confirm(client, token, wrong).status_code == 400

    challenge = TwoFactorChallenge.query.one()
    assert challenge.attempt_count == cap
    assert challenge.consumed_at is not None

    # Dead afterwards, even for the correct code.
    assert _confirm(client, token, code).status_code == 400


def test_a_password_below_the_minimum_length_is_rejected(
    client, make_user, sent_codes
):
    minimum = two_factor_service.PASSWORD_RESET_MIN_LENGTH
    user = make_user("customer")
    token, code = _start_reset(client, sent_codes, user)

    short = _confirm(client, token, code, password="a" * (minimum - 1))
    assert short.status_code == 400
    assert str(minimum) in short.get_json()["message"]

    # Rejected before the challenge was touched, so it is still usable.
    assert _confirm(
        client, token, code, password="a" * minimum
    ).status_code == 200


# --------------------------------------------------------------------------- #
# Accounts that may not reset
# --------------------------------------------------------------------------- #

def test_a_deleted_account_is_refused_indistinguishably(
    client, make_user, sent_codes
):
    live = make_user("customer", email="live@test.local")
    gone = make_user("customer", email="gone@test.local")
    gone.deleted_at = two_factor_service.utcnow()
    db.session.commit()

    live_body = _request(client, live.email).get_json()
    gone_body = _request(client, gone.email).get_json()

    assert live_body.keys() == gone_body.keys()
    assert live_body["message"] == gone_body["message"]
    # No code was sent for the deleted account, and no challenge exists.
    assert [email for email, _ in sent_codes] == [live.email]
    assert TwoFactorChallenge.query.filter_by(user_id=gone.id).count() == 0
    assert _confirm(
        client, gone_body["challenge_token"], "000000"
    ).status_code == 400


def test_a_deactivated_account_is_refused_indistinguishably(
    client, make_user, sent_codes
):
    user = make_user("customer")
    user.is_active = False
    db.session.commit()

    body = _request(client, user.email).get_json()

    assert body["method"] == "email"
    assert sent_codes == []
    assert TwoFactorChallenge.query.count() == 0


@pytest.mark.xfail(
    strict=True,
    reason=(
        "KNOWN GAP, reported and not yet fixed: _account_can_reset checks "
        "deleted_at and is_active but not suspended_at, so a suspended "
        "account can complete a password reset. Login still refuses it "
        "(403), so this is not an escalation — but the reset should not "
        "be reachable. Remove this marker when the check includes "
        "suspended_at."
    ),
)
def test_a_suspended_account_cannot_reset_its_password(
    client, make_user, sent_codes
):
    user = make_user("customer")
    user.suspended_at = two_factor_service.utcnow()
    db.session.commit()

    _request(client, user.email)
    assert sent_codes == []
    assert TwoFactorChallenge.query.count() == 0


@pytest.mark.xfail(
    strict=True,
    reason=(
        "KNOWN GAP, reported and not yet fixed: _account_can_reset does not "
        "check is_verified, so an address that was never confirmed can be "
        "sent a reset code. Remove this marker when the check includes "
        "is_verified."
    ),
)
def test_an_unverified_account_cannot_reset_its_password(
    client, make_user, sent_codes
):
    user = make_user("customer", is_verified=False)
    db.session.commit()

    _request(client, user.email)
    assert sent_codes == []
    assert TwoFactorChallenge.query.count() == 0


# --------------------------------------------------------------------------- #
# Storage and session invalidation
# --------------------------------------------------------------------------- #

def test_the_challenge_token_is_stored_hashed_not_in_plaintext(
    client, make_user, sent_codes
):
    user = make_user("customer")
    token, _ = _start_reset(client, sent_codes, user)

    challenge = TwoFactorChallenge.query.one()
    assert challenge.token_hash != token
    assert challenge.token_hash == hashlib.sha256(
        token.encode("utf-8")
    ).hexdigest()

    # The plaintext token appears in no column of the row.
    stored = [
        str(getattr(challenge, column.name))
        for column in TwoFactorChallenge.__table__.columns
    ]
    assert not any(token in value for value in stored)


def test_resetting_the_password_kills_tokens_issued_before_it(
    client, make_user, sent_codes
):
    """A stolen session must not outlive the password it was riding on."""
    user = make_user("customer")

    login = client.post(
        "/api/auth/login",
        json={"email": user.email, "password": user.plain_password},
    )
    assert login.status_code == 202
    verified = client.post(
        "/api/auth/login/verify",
        json={
            "challenge_token": login.get_json()["challenge_token"],
            "code": sent_codes.last,
        },
    )
    assert verified.status_code == 200
    old_token = verified.get_json()["access_token"]
    old_header = {"Authorization": f"Bearer {old_token}"}

    # The session works before the reset.
    assert client.get("/api/notifications", headers=old_header).status_code == 200

    token, code = _start_reset(client, sent_codes, user)
    assert _confirm(client, token, code).status_code == 200

    db.session.refresh(user)
    assert user.tokens_revoked_at is not None

    after = client.get("/api/notifications", headers=old_header)
    assert after.status_code == 401, (
        "an access token minted before the password reset still "
        "authenticates — the reset did not revoke live sessions"
    )


def test_the_new_password_hash_is_stored_not_the_password(
    client, make_user, sent_codes
):
    user = make_user("customer")
    token, code = _start_reset(client, sent_codes, user)
    assert _confirm(client, token, code).status_code == 200

    db.session.refresh(user)
    stored = db.session.get(User, user.id).password
    assert NEW_PASSWORD not in stored
    assert stored.startswith(("pbkdf2:", "scrypt:", "argon2"))
