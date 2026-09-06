"""Theme preference — light, dark or follow the device.

Stored on the account beside `language` and `currency`, so it travels
with the person rather than with the browser. The client-side half of the
feature (which attribute lands on `<html>`, and whether an explicit light
choice beats a dark device) is tested in
frontend/src/utils/theme.test.js, where the logic actually lives.
"""

import pytest

from app.models.user import User


def _put(client, auth, user, theme, as_user=None):
    return client.put(
        f"/api/users/{user.id}/theme",
        json={"theme": theme},
        headers=auth(as_user or user),
    )


def test_a_new_user_follows_the_system(make_user):
    """The only value that is right before anyone has been asked."""
    assert make_user("customer").theme == "system"


@pytest.mark.parametrize("theme", ["light", "dark", "system"])
def test_the_preference_round_trips(client, auth, make_user, db, theme):
    user = make_user("customer")

    response = _put(client, auth, user, theme)

    assert response.status_code == 200
    assert response.get_json()["user"]["theme"] == theme

    db.session.expire_all()
    assert db.session.get(User, user.id).theme == theme


def test_it_comes_back_on_the_profile(client, auth, make_user):
    user = make_user("customer")
    _put(client, auth, user, "dark")

    body = client.get(
        f"/api/users/{user.id}", headers=auth(user)
    ).get_json()

    assert body["user"]["theme"] == "dark"


def test_a_choice_survives_being_changed_again(client, auth, make_user, db):
    user = make_user("customer")

    _put(client, auth, user, "dark")
    _put(client, auth, user, "light")

    db.session.expire_all()
    assert db.session.get(User, user.id).theme == "light"


@pytest.mark.parametrize(
    "theme", ["solarized", "Dark", "", None, 1, "light "]
)
def test_an_unsupported_theme_is_refused(client, auth, make_user, db, theme):
    user = make_user("customer")

    response = _put(client, auth, user, theme)

    assert response.status_code == 400
    db.session.expire_all()
    assert db.session.get(User, user.id).theme == "system"


def test_one_user_cannot_set_another_users_theme(
    client, auth, make_user, db
):
    victim = make_user("customer")
    intruder = make_user("customer")

    response = _put(client, auth, victim, "dark", as_user=intruder)

    assert response.status_code == 403
    db.session.expire_all()
    assert db.session.get(User, victim.id).theme == "system"


def test_a_signed_out_visitor_cannot_set_a_theme(client, make_user):
    user = make_user("customer")

    response = client.put(
        f"/api/users/{user.id}/theme", json={"theme": "dark"}
    )

    assert response.status_code == 401
