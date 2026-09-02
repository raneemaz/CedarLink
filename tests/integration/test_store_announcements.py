"""Store announcements (C.1) — CRUD, the live-window rule, the active cap,
and the optional promotions notification to a store's past customers.
"""

from datetime import datetime, timedelta, timezone

from app.extensions import db
from app.models.notification import Notification
from app.models.notification_preferences import NotificationPreferences
from app.services import announcement_service


def _iso(dt):
    return dt.replace(microsecond=0).isoformat()


def _future(hours):
    return _iso(datetime.now(timezone.utc) + timedelta(hours=hours))


def _past(hours):
    return _iso(datetime.now(timezone.utc) - timedelta(hours=hours))


def _create(client, auth, store, **body):
    return client.post(
        f"/api/stores/{store.id}/announcements",
        json={"title": "Eid hours", "body": "Open 10-14 only.", **body},
        headers=auth(store.owner),
    )


# --------------------------------------------------------------------------- #
# CRUD + ownership
# --------------------------------------------------------------------------- #

def test_create_list_update_delete_round_trip(client, auth, make_store):
    store = make_store()

    created = _create(client, auth, store, title="Ramadan", body="Late nights.")
    assert created.status_code == 201
    aid = created.get_json()["announcement"]["id"]

    listed = client.get(f"/api/stores/{store.id}/announcements").get_json()
    assert [a["title"] for a in listed["announcements"]] == ["Ramadan"]

    updated = client.put(
        f"/api/stores/{store.id}/announcements/{aid}",
        json={"title": "Ramadan 2026"},
        headers=auth(store.owner),
    )
    assert updated.status_code == 200
    assert updated.get_json()["announcement"]["title"] == "Ramadan 2026"

    deleted = client.delete(
        f"/api/stores/{store.id}/announcements/{aid}",
        headers=auth(store.owner),
    )
    assert deleted.status_code == 200
    assert client.get(
        f"/api/stores/{store.id}/announcements"
    ).get_json()["announcements"] == []


def test_create_requires_title_and_body(client, auth, make_store):
    store = make_store()
    assert _create(client, auth, store, title="").status_code == 400
    assert _create(client, auth, store, body="  ").status_code == 400


def test_non_owner_and_customer_cannot_write(
    client, auth, make_store, make_user, customer
):
    store = make_store()
    intruder = make_user("vendor", email="intruder-ann@test.local")

    assert client.post(
        f"/api/stores/{store.id}/announcements",
        json={"title": "x", "body": "y"},
        headers=auth(intruder),
    ).status_code == 403
    assert client.post(
        f"/api/stores/{store.id}/announcements",
        json={"title": "x", "body": "y"},
        headers=auth(customer),
    ).status_code == 403


def test_update_delete_reject_another_stores_announcement(
    client, auth, make_store
):
    store_a = make_store()
    store_b = make_store()
    aid = _create(client, auth, store_a).get_json()["announcement"]["id"]

    assert client.put(
        f"/api/stores/{store_b.id}/announcements/{aid}",
        json={"title": "hijack"},
        headers=auth(store_b.owner),
    ).status_code == 404
    assert client.delete(
        f"/api/stores/{store_b.id}/announcements/{aid}",
        headers=auth(store_b.owner),
    ).status_code == 404


# --------------------------------------------------------------------------- #
# Live-window rule
# --------------------------------------------------------------------------- #

def test_public_list_shows_only_live_announcements(client, auth, make_store):
    store = make_store()
    _create(client, auth, store, title="Now on")
    _create(client, auth, store, title="Starts later", starts_at=_future(48))
    _create(client, auth, store, title="Already ended", ends_at=_past(1))
    _create(client, auth, store, title="Switched off", is_active=False)

    public = client.get(
        f"/api/stores/{store.id}/announcements"
    ).get_json()["announcements"]
    assert [a["title"] for a in public] == ["Now on"]

    # The owner sees every row, each flagged with is_live.
    owner = client.get(
        f"/api/stores/{store.id}/announcements",
        headers=auth(store.owner),
    ).get_json()["announcements"]
    by_title = {a["title"]: a["is_live"] for a in owner}
    assert by_title == {
        "Now on": True,
        "Starts later": False,
        "Already ended": False,
        "Switched off": False,
    }


def test_ends_at_must_be_after_starts_at(client, auth, make_store):
    store = make_store()
    resp = _create(
        client, auth, store, starts_at=_future(10), ends_at=_future(2)
    )
    assert resp.status_code == 400


# --------------------------------------------------------------------------- #
# Active cap
# --------------------------------------------------------------------------- #

def test_a_store_is_capped_at_five_active_announcements(
    client, auth, make_store
):
    store = make_store()
    for i in range(announcement_service.MAX_ACTIVE_PER_STORE):
        assert _create(client, auth, store, title=f"A{i}").status_code == 201

    sixth = _create(client, auth, store, title="A6")
    assert sixth.status_code == 400

    # An inactive one is fine, and can be re-activated only if there is room.
    inactive = _create(client, auth, store, title="Draft", is_active=False)
    assert inactive.status_code == 201
    aid = inactive.get_json()["announcement"]["id"]

    assert client.put(
        f"/api/stores/{store.id}/announcements/{aid}",
        json={"is_active": True},
        headers=auth(store.owner),
    ).status_code == 400


# --------------------------------------------------------------------------- #
# Promotions notification
# --------------------------------------------------------------------------- #

def test_announcement_notifies_past_customers_who_opted_in(
    client, auth, make_store, make_product, make_order, make_user
):
    store = make_store()
    product = make_product(store=store)

    opted_in = make_user("customer", email="opted-in@test.local")
    opted_out = make_user("customer", email="opted-out@test.local")
    db.session.add(
        NotificationPreferences(user_id=opted_in.id, promotions=True)
    )
    db.session.commit()

    make_order(customer=opted_in, product=product)
    make_order(customer=opted_out, product=product)

    resp = _create(client, auth, store, title="Fresh stock", body="Come by!")
    assert resp.status_code == 201

    notes = Notification.query.filter_by(type="store_announcement").all()
    assert [n.user_id for n in notes] == [opted_in.id]
    assert notes[0].title == "Fresh stock"
    assert notes[0].link == f"/stores/{store.id}"


def test_inactive_announcement_does_not_notify(
    client, auth, make_store, make_product, make_order, make_user
):
    store = make_store()
    product = make_product(store=store)
    customer = make_user("customer", email="c-inactive@test.local")
    db.session.add(
        NotificationPreferences(user_id=customer.id, promotions=True)
    )
    db.session.commit()
    make_order(customer=customer, product=product)

    _create(client, auth, store, is_active=False)

    assert Notification.query.filter_by(type="store_announcement").count() == 0
