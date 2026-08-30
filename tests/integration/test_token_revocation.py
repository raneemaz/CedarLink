"""CL-09 — a JWT can be killed before it expires.

Logout revokes the token it was called with; admin suspension, password
reset and self-deactivation revoke every token the user holds. The check
runs on the next request, not 15 minutes later.
"""

from app.extensions import db
from app.models.token_denylist import TokenDenylist


def test_logout_revokes_the_current_token(client, auth, customer):
    headers = auth(customer)
    assert client.get("/api/orders", headers=headers).status_code == 200

    logout = client.post("/api/auth/logout", headers=headers)
    assert logout.status_code == 200

    reused = client.get("/api/orders", headers=headers)
    assert reused.status_code == 401
    assert db.session.query(TokenDenylist).count() == 1


def test_a_fresh_login_after_logout_still_works(client, auth, customer):
    old = auth(customer)
    client.post("/api/auth/logout", headers=old)

    fresh = auth(customer)
    assert client.get("/api/orders", headers=fresh).status_code == 200


def test_suspended_users_live_token_is_rejected_on_the_next_request(
    client, auth, admin, make_user
):
    victim = make_user("customer", email="victim-token@test.local")
    headers = auth(victim)
    assert client.get("/api/orders", headers=headers).status_code == 200

    suspend = client.patch(
        f"/api/admin/users/{victim.id}/suspend",
        json={"reason": "abuse"},
        headers=auth(admin),
    )
    assert suspend.status_code == 200

    # Same token the victim was already holding — not re-issued.
    blocked = client.get("/api/orders", headers=headers)
    assert blocked.status_code == 401


def test_suspending_one_user_does_not_revoke_another(
    client, auth, admin, make_user
):
    a = make_user("customer", email="keep-a@test.local")
    b = make_user("customer", email="suspend-b@test.local")
    a_headers = auth(a)

    client.patch(
        f"/api/admin/users/{b.id}/suspend",
        json={},
        headers=auth(admin),
    )

    assert client.get("/api/orders", headers=a_headers).status_code == 200
