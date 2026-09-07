"""ADR 0033 §5 item 9 — PUT /api/users/<id> no longer confirms an email
exists.

It used to return 400 "Email already exists" when you tried to change
your own email to a taken one — an existence oracle (authenticated,
own-account only, but real). Now it matches the decoy-success pattern
registration uses: the other fields update, the email changes only when
it is both new and free, and the response is identical either way, with
the real stored email echoed back.
"""


def _put(client, auth, user, email):
    return client.put(
        f"/api/users/{user.id}",
        headers=auth(user),
        json={
            "first_name": "New", "last_name": "Name",
            "email": email, "phone": "+9613111111",
        },
    )


def test_changing_email_to_a_taken_one_looks_exactly_like_success(
    client, auth, make_user
):
    victim = make_user("customer", email="taken@enum.local")
    attacker = make_user("customer", email="attacker@enum.local")

    taken = _put(client, auth, attacker, "taken@enum.local")
    free = _put(client, auth, attacker, "brand-new@enum.local")

    # Same status, same body shape, no "already exists" anywhere.
    assert taken.status_code == free.status_code == 200
    assert taken.get_json().keys() == free.get_json().keys()
    body = taken.get_data(as_text=True).lower()
    assert "exist" not in body and "taken" not in body

    _ = victim  # (fixture kept for the collision)


def test_the_taken_email_is_not_applied_but_the_other_fields_are(
    client, auth, make_user
):
    make_user("customer", email="occupied@enum.local")
    attacker = make_user("customer", email="me@enum.local")

    resp = _put(client, auth, attacker, "occupied@enum.local")

    assert resp.status_code == 200
    assert resp.get_json()["user"]["email"] == "me@enum.local"  # unchanged
    assert resp.get_json()["user"]["first_name"] == "New"       # applied


def test_a_genuinely_free_email_change_still_works(client, auth, make_user):
    user = make_user("customer", email="before@enum.local")

    resp = _put(client, auth, user, "after@enum.local")

    assert resp.status_code == 200
    assert resp.get_json()["user"]["email"] == "after@enum.local"
