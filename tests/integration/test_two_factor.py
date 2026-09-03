"""Two-factor authentication.

Covers setup/confirm, the login challenge, recovery codes, and the security
proof required to weaken or remove the second factor. The questions these
answer: is 2FA actually enforced at login, is the secret safe at rest, is a
challenge bound to one user and one purpose, and can anything be replayed.
"""

import pyotp
import pytest

from app.extensions import db
from app.models.two_factor_challenge import TwoFactorChallenge
from app.models.two_factor_recovery_code import TwoFactorRecoveryCode
from app.services import two_factor_service

LOGIN_URL = "/api/auth/login"
VERIFY_URL = "/api/auth/login/verify"


def _setup_url(user):
    return f"/api/users/{user.id}/2fa/setup"


def _confirm_url(user):
    return f"/api/users/{user.id}/2fa/confirm"


def _security_url(user):
    return f"/api/users/{user.id}/2fa/security-challenge"


def _login(client, user, password=None):
    return client.post(
        LOGIN_URL,
        json={
            "email": user.email,
            "password": password or user.plain_password,
        },
    )


def _security_proof(client, auth, user, totp_code, secret):
    """Password + TOTP proof; returns the challenge_token/code pair."""
    challenge = client.post(
        _security_url(user),
        json={"current_password": user.plain_password},
        headers=auth(user),
    )
    assert challenge.status_code == 201, challenge.get_json()
    return {
        "challenge_token": challenge.get_json()["challenge_token"],
        "code": totp_code(secret),
    }


# --------------------------------------------------------------------------- #
# Setup and confirmation
# --------------------------------------------------------------------------- #

def test_setup_alone_does_not_enable_two_factor(
    client, auth, make_user, totp_code
):
    user = make_user("customer")

    started = client.post(
        _setup_url(user), json={"method": "totp"}, headers=auth(user)
    )
    assert started.status_code == 201
    body = started.get_json()
    assert "manual_key" in body and "qr_code_data_url" in body

    db.session.refresh(user)
    assert user.two_factor_enabled is False
    assert user.two_factor_totp_secret is None

    status = client.get(f"/api/users/{user.id}/2fa", headers=auth(user))
    assert status.get_json() == {
        "two_factor_enabled": False,
        "two_factor_method": None,
    }

    # And login is unchanged: still the plain email challenge, not TOTP.
    login = _login(client, user)
    assert login.status_code == 202
    assert login.get_json()["method"] == "email"


def test_confirm_enables_two_factor_and_returns_recovery_codes(
    client, auth, make_user, totp_code
):
    user = make_user("customer")
    body = client.post(
        _setup_url(user), json={"method": "totp"}, headers=auth(user)
    ).get_json()

    confirmed = client.post(
        _confirm_url(user),
        json={
            "challenge_token": body["challenge_token"],
            "code": totp_code(body["manual_key"]),
        },
        headers=auth(user),
    )
    assert confirmed.status_code == 200
    payload = confirmed.get_json()
    assert payload["two_factor_enabled"] is True
    assert payload["two_factor_method"] == "totp"
    assert len(payload["recovery_codes"]) == 10

    db.session.refresh(user)
    assert user.two_factor_enabled is True
    assert user.two_factor_method == "totp"


def test_a_wrong_setup_code_leaves_two_factor_off(
    client, auth, make_user
):
    user = make_user("customer")
    body = client.post(
        _setup_url(user), json={"method": "totp"}, headers=auth(user)
    ).get_json()

    rejected = client.post(
        _confirm_url(user),
        json={"challenge_token": body["challenge_token"], "code": "000000"},
        headers=auth(user),
    )
    assert rejected.status_code == 400

    db.session.refresh(user)
    assert user.two_factor_enabled is False


def test_the_totp_secret_is_encrypted_at_rest(
    client, auth, make_user, totp_code
):
    user = make_user("customer")
    body = client.post(
        _setup_url(user), json={"method": "totp"}, headers=auth(user)
    ).get_json()
    secret = body["manual_key"]

    # Before confirmation the secret already sits on the challenge row.
    challenge = TwoFactorChallenge.query.one()
    assert challenge.totp_secret_encrypted != secret
    assert secret not in challenge.totp_secret_encrypted

    client.post(
        _confirm_url(user),
        json={
            "challenge_token": body["challenge_token"],
            "code": totp_code(secret),
        },
        headers=auth(user),
    )

    # Read the column straight out of the database, not through the service.
    stored = db.session.execute(
        db.text("SELECT two_factor_totp_secret FROM users WHERE id = :id"),
        {"id": user.id},
    ).scalar_one()
    assert stored != secret
    assert secret not in stored
    assert two_factor_service.decrypt_totp_secret(stored) == secret


# --------------------------------------------------------------------------- #
# Login enforcement — the test that decides whether 2FA is real
# --------------------------------------------------------------------------- #

def test_login_with_two_factor_returns_a_challenge_and_no_usable_token(
    client, make_totp_user
):
    user, _secret = make_totp_user()

    response = _login(client, user)
    assert response.status_code == 202
    body = response.get_json()

    assert body["verification_required"] is True
    assert body["method"] == "totp"
    assert "access_token" not in body
    assert "refresh_token" not in body

    # Nothing token-shaped in the payload authenticates a request.
    for key, value in body.items():
        if not isinstance(value, str) or len(value) < 20:
            continue
        probe = client.get(
            "/api/notifications",
            headers={"Authorization": f"Bearer {value}"},
        )
        # 401 for a rejected JWT, 422 for one that is not a JWT at all —
        # the challenge_token is opaque, not a token. Either is a refusal.
        assert probe.status_code in (401, 422), (
            f"the value under {key!r} in the login response authenticates a "
            "request — the second factor can be skipped"
        )


def test_confirming_totp_actually_changes_what_login_asks_for(
    client, auth, make_user, totp_code, sent_codes
):
    user = make_user("customer")  # verification_method == "email"
    body = client.post(
        _setup_url(user), json={"method": "totp"}, headers=auth(user)
    ).get_json()
    confirmed = client.post(
        _confirm_url(user),
        json={
            "challenge_token": body["challenge_token"],
            "code": totp_code(body["manual_key"]),
        },
        headers=auth(user),
    )
    assert confirmed.status_code == 200

    login = _login(client, user)
    assert login.status_code == 202
    assert login.get_json()["method"] == "totp"
    assert sent_codes == [], (
        "an email code was sent even though the user's second factor is an "
        "authenticator app"
    )


def test_a_legacy_row_with_a_stale_verification_method_is_challenged_by_totp(
    client, make_user, totp_code, sent_codes
):
    """The state every pre-fix TOTP user is already in.

    No data migration backfills these rows; create_login_challenge simply
    stops consulting verification_method once a second factor is set, so
    they are covered by precedence alone.
    """
    user = make_user("customer")
    secret = pyotp.random_base32()
    user.verification_method = "email"        # never rewritten by setup
    user.two_factor_enabled = True
    user.two_factor_method = "totp"
    user.two_factor_totp_secret = two_factor_service.encrypt_totp_secret(
        secret
    )
    db.session.commit()

    login = _login(client, user)
    assert login.status_code == 202
    assert login.get_json()["method"] == "totp"
    assert sent_codes == []

    verified = client.post(
        VERIFY_URL,
        json={
            "challenge_token": login.get_json()["challenge_token"],
            "code": totp_code(secret),
        },
    )
    assert verified.status_code == 200


def test_completing_the_challenge_returns_working_tokens(
    client, make_totp_user, totp_code
):
    user, secret = make_totp_user()
    token = _login(client, user).get_json()["challenge_token"]

    verified = client.post(
        VERIFY_URL, json={"challenge_token": token, "code": totp_code(secret)}
    )
    assert verified.status_code == 200
    tokens = verified.get_json()
    assert tokens["access_token"] and tokens["refresh_token"]

    ok = client.get(
        "/api/notifications",
        headers={"Authorization": f"Bearer {tokens['access_token']}"},
    )
    assert ok.status_code == 200


def test_a_wrong_totp_code_is_rejected(client, make_totp_user, totp_code):
    user, secret = make_totp_user()
    token = _login(client, user).get_json()["challenge_token"]

    bad = client.post(
        VERIFY_URL, json={"challenge_token": token, "code": "000000"}
    )
    assert bad.status_code == 400

    # One miss does not burn the challenge.
    good = client.post(
        VERIFY_URL, json={"challenge_token": token, "code": totp_code(secret)}
    )
    assert good.status_code == 200


def test_repeated_wrong_codes_exhaust_the_login_challenge(
    client, app, make_totp_user, totp_code
):
    cap = app.config["TWO_FACTOR_MAX_ATTEMPTS"]
    user, secret = make_totp_user()
    token = _login(client, user).get_json()["challenge_token"]

    for _ in range(cap):
        assert client.post(
            VERIFY_URL, json={"challenge_token": token, "code": "000000"}
        ).status_code == 400

    challenge = TwoFactorChallenge.query.one()
    assert challenge.attempt_count == cap
    assert challenge.consumed_at is not None

    dead = client.post(
        VERIFY_URL, json={"challenge_token": token, "code": totp_code(secret)}
    )
    assert dead.status_code == 400


@pytest.mark.xfail(
    strict=True,
    reason=(
        "KNOWN DEFECT, reported and not yet fixed: _verify_challenge_code "
        "calls pyotp.TOTP.verify with no record of consumed codes, so a "
        "code observed once stays valid against a fresh login challenge "
        "for the rest of its time step (up to ~90s with valid_window=1). "
        "Remove this marker when the service tracks used counters."
    ),
)
def test_a_totp_code_cannot_be_replayed_against_a_fresh_challenge(
    client, make_totp_user, totp_code
):
    """RFC 6238 §5.2: a TOTP code must be accepted at most once.

    The first challenge is consumed on success, so a replay needs a *new*
    challenge — exactly what an attacker who shoulder-surfed the code has.
    """
    user, secret = make_totp_user()
    code = totp_code(secret)

    first = _login(client, user).get_json()["challenge_token"]
    assert client.post(
        VERIFY_URL, json={"challenge_token": first, "code": code}
    ).status_code == 200

    second = _login(client, user).get_json()["challenge_token"]
    replay = client.post(
        VERIFY_URL, json={"challenge_token": second, "code": code}
    )
    assert replay.status_code == 400, (
        "the same TOTP code was accepted twice — an observed code stays "
        "usable for the rest of its time step"
    )


# --------------------------------------------------------------------------- #
# Recovery codes
# --------------------------------------------------------------------------- #

def test_a_recovery_code_works_once_and_only_once(
    client, make_totp_user, make_recovery_codes
):
    user, _secret = make_totp_user()
    codes = make_recovery_codes(user)

    first_token = _login(client, user).get_json()["challenge_token"]
    used = client.post(
        VERIFY_URL,
        json={
            "challenge_token": first_token,
            "code": codes[0],
            "use_recovery_code": True,
        },
    )
    assert used.status_code == 200
    assert used.get_json()["access_token"]

    second_token = _login(client, user).get_json()["challenge_token"]
    reuse = client.post(
        VERIFY_URL,
        json={
            "challenge_token": second_token,
            "code": codes[0],
            "use_recovery_code": True,
        },
    )
    assert reuse.status_code == 400

    row = TwoFactorRecoveryCode.query.filter_by(used=True).one()
    assert row.used_at is not None

    # A different unused code still works.
    third_token = _login(client, user).get_json()["challenge_token"]
    assert client.post(
        VERIFY_URL,
        json={
            "challenge_token": third_token,
            "code": codes[1],
            "use_recovery_code": True,
        },
    ).status_code == 200


def test_recovery_codes_are_stored_hashed(
    client, make_totp_user, make_recovery_codes
):
    user, _secret = make_totp_user()
    codes = make_recovery_codes(user)

    rows = TwoFactorRecoveryCode.query.all()
    assert len(rows) == len(codes) == 10

    hashes = [row.code_hash for row in rows]
    for code in codes:
        assert code not in hashes
        normalized = two_factor_service._normalize_recovery_code(code)
        assert not any(normalized in stored for stored in hashes)
    assert all(row.code_hash.startswith(("pbkdf2:", "scrypt:")) for row in rows)


def test_regenerating_recovery_codes_kills_every_old_one(
    client, auth, make_totp_user, make_recovery_codes, totp_code
):
    user, secret = make_totp_user()
    old_codes = make_recovery_codes(user)

    regenerated = client.post(
        f"/api/users/{user.id}/2fa/recovery-codes/regenerate",
        json=_security_proof(client, auth, user, totp_code, secret),
        headers=auth(user),
    )
    assert regenerated.status_code == 200
    new_codes = regenerated.get_json()["recovery_codes"]
    assert set(new_codes).isdisjoint(old_codes)
    assert TwoFactorRecoveryCode.query.count() == 10

    token = _login(client, user).get_json()["challenge_token"]
    assert client.post(
        VERIFY_URL,
        json={
            "challenge_token": token,
            "code": old_codes[0],
            "use_recovery_code": True,
        },
    ).status_code == 400


# --------------------------------------------------------------------------- #
# Weakening the second factor needs proof, not just a session
# --------------------------------------------------------------------------- #

def test_disabling_two_factor_needs_a_security_challenge(
    client, auth, make_totp_user, totp_code
):
    user, secret = make_totp_user()

    # Signed in, but with no proof at all.
    bare = client.post(
        f"/api/users/{user.id}/2fa/disable", json={}, headers=auth(user)
    )
    assert bare.status_code == 400
    db.session.refresh(user)
    assert user.two_factor_enabled is True

    # A security challenge also needs the current password.
    wrong_password = client.post(
        _security_url(user),
        json={"current_password": "not-the-password"},
        headers=auth(user),
    )
    assert wrong_password.status_code == 401

    proof = _security_proof(client, auth, user, totp_code, secret)
    disabled = client.post(
        f"/api/users/{user.id}/2fa/disable", json=proof, headers=auth(user)
    )
    assert disabled.status_code == 200

    db.session.refresh(user)
    assert user.two_factor_enabled is False
    assert user.two_factor_totp_secret is None
    assert TwoFactorRecoveryCode.query.count() == 0


def test_changing_the_two_factor_method_needs_the_same_proof(
    client, auth, make_totp_user, totp_code, sent_codes
):
    user, secret = make_totp_user()

    bare = client.post(
        f"/api/users/{user.id}/2fa/change-method",
        json={"method": "email"},
        headers=auth(user),
    )
    assert bare.status_code == 400
    db.session.refresh(user)
    assert user.two_factor_method == "totp"

    proof = _security_proof(client, auth, user, totp_code, secret)
    changed = client.post(
        f"/api/users/{user.id}/2fa/change-method",
        json={"method": "email", **proof},
        headers=auth(user),
    )
    assert changed.status_code == 201

    # Still TOTP until the new method is confirmed.
    db.session.refresh(user)
    assert user.two_factor_method == "totp"

    confirmed = client.post(
        _confirm_url(user),
        json={
            "challenge_token": changed.get_json()["challenge_token"],
            "code": sent_codes.last,
        },
        headers=auth(user),
    )
    assert confirmed.status_code == 200
    db.session.refresh(user)
    assert user.two_factor_method == "email"
    assert user.two_factor_totp_secret is None


# --------------------------------------------------------------------------- #
# Challenge binding: to a user, and to a purpose
# --------------------------------------------------------------------------- #

def test_a_challenge_issued_for_one_user_cannot_be_used_by_another(
    client, auth, make_totp_user, totp_code
):
    victim, victim_secret = make_totp_user(email="victim@test.local")
    attacker, attacker_secret = make_totp_user(email="attacker@test.local")

    stolen = client.post(
        _security_url(victim),
        json={"current_password": victim.plain_password},
        headers=auth(victim),
    ).get_json()["challenge_token"]

    hijack = client.post(
        f"/api/users/{attacker.id}/2fa/disable",
        json={"challenge_token": stolen, "code": totp_code(attacker_secret)},
        headers=auth(attacker),
    )
    assert hijack.status_code == 400
    assert "does not belong" in hijack.get_json()["message"]

    db.session.refresh(attacker)
    assert attacker.two_factor_enabled is True


def test_a_setup_challenge_cannot_be_confirmed_by_another_user(
    client, auth, make_user, totp_code
):
    owner = make_user("customer", email="setup-owner@test.local")
    stranger = make_user("customer", email="setup-stranger@test.local")

    body = client.post(
        _setup_url(owner), json={"method": "totp"}, headers=auth(owner)
    ).get_json()

    hijack = client.post(
        _confirm_url(stranger),
        json={
            "challenge_token": body["challenge_token"],
            "code": totp_code(body["manual_key"]),
        },
        headers=auth(stranger),
    )
    assert hijack.status_code == 400
    db.session.refresh(stranger)
    assert stranger.two_factor_enabled is False


def test_a_login_challenge_does_not_satisfy_a_security_endpoint(
    client, auth, make_totp_user, totp_code
):
    """Purpose is part of the lookup: login/security/password_reset/setup
    challenges are not interchangeable."""
    user, secret = make_totp_user()
    login_token = _login(client, user).get_json()["challenge_token"]

    # As a security proof (disable 2FA).
    as_security = client.post(
        f"/api/users/{user.id}/2fa/disable",
        json={"challenge_token": login_token, "code": totp_code(secret)},
        headers=auth(user),
    )
    assert as_security.status_code == 400
    db.session.refresh(user)
    assert user.two_factor_enabled is True

    # As a password-reset proof.
    as_reset = client.post(
        "/api/auth/password-reset/confirm",
        json={
            "challenge_token": login_token,
            "code": totp_code(secret),
            "new_password": "Hijacked-Passw0rd",
        },
    )
    assert as_reset.status_code == 400

    # As a setup proof.
    as_setup = client.post(
        _confirm_url(user),
        json={"challenge_token": login_token, "code": totp_code(secret)},
        headers=auth(user),
    )
    assert as_setup.status_code == 400

    # The login challenge itself is untouched and still works.
    assert client.post(
        VERIFY_URL,
        json={"challenge_token": login_token, "code": totp_code(secret)},
    ).status_code == 200


def test_a_password_reset_challenge_does_not_satisfy_login(
    client, make_user, sent_codes
):
    user = make_user("customer")
    reset = client.post(
        "/api/auth/password-reset/request", json={"email": user.email}
    ).get_json()

    hijack = client.post(
        VERIFY_URL,
        json={"challenge_token": reset["challenge_token"],
              "code": sent_codes.last},
    )
    assert hijack.status_code == 400


# --------------------------------------------------------------------------- #
# Expiry
# --------------------------------------------------------------------------- #

def test_an_expired_login_challenge_is_rejected(
    client, make_totp_user, totp_code
):
    user, secret = make_totp_user()
    token = _login(client, user).get_json()["challenge_token"]

    challenge = TwoFactorChallenge.query.one()
    challenge.expires_at = two_factor_service.utcnow().replace(year=2000)
    db.session.commit()

    expired = client.post(
        VERIFY_URL, json={"challenge_token": token, "code": totp_code(secret)}
    )
    assert expired.status_code == 400
    assert "expired" in expired.get_json()["message"].lower()
