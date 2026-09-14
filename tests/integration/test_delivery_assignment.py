"""Delivery assignments — the driver's phone is a scoped disclosure, not a
field in the dump (docs/decisions/0019)."""

import pytest

from app.models.delivery_assignment import DeliveryAssignment
from app.services import delivery_service


def _assign(client, auth, order):
    return client.post(
        "/api/delivery/assignments",
        json={
            "order_id": order.id,
            "driver_name": "Karim Aoun",
            "driver_phone": "+961 3 111 222",
        },
        headers=auth(order.store.owner),
    )


def _advance(client, auth, order, assignment_id, status):
    return client.patch(
        f"/api/delivery/assignments/{assignment_id}/status",
        json={"status": status},
        headers=auth(order.store.owner),
    )


def _get(client, auth, user, assignment_id):
    return client.get(
        f"/api/delivery/assignments/{assignment_id}", headers=auth(user)
    ).get_json()["delivery_assignment"]


def test_to_dict_omits_driver_phone_unless_asked(db, make_order):
    order = make_order()
    a = DeliveryAssignment(
        order_id=order.id, driver_name="X", driver_phone="+961 3 000 000"
    )
    db.session.add(a)
    db.session.flush()

    assert "driver_phone" not in a.to_dict()
    assert a.to_dict(include_driver_phone=True)["driver_phone"] == (
        "+961 3 000 000"
    )


def test_customer_sees_driver_phone_while_delivery_is_in_progress(
    client, auth, make_order
):
    order = make_order(status="processing")
    aid = _assign(client, auth, order).get_json()["delivery_assignment"]["id"]

    # assigned
    assigned = _get(client, auth, order.user, aid)
    assert assigned["driver_phone"] == "+961 3 111 222"

    # picked up
    _advance(client, auth, order, aid, "picked_up")
    picked = _get(client, auth, order.user, aid)
    assert picked["driver_phone"] == "+961 3 111 222"


def test_customer_loses_the_phone_once_delivered_but_keeps_the_name(
    client, auth, make_order
):
    order = make_order(status="processing")
    aid = _assign(client, auth, order).get_json()["delivery_assignment"]["id"]
    _advance(client, auth, order, aid, "picked_up")
    _advance(client, auth, order, aid, "delivered")

    seen = _get(client, auth, order.user, aid)
    assert "driver_phone" not in seen
    assert seen["driver_name"] == "Karim Aoun"


def test_vendor_keeps_the_driver_phone_after_delivery(
    client, auth, make_order
):
    order = make_order(status="processing")
    created = _assign(client, auth, order).get_json()["delivery_assignment"]
    assert created["driver_phone"] == "+961 3 111 222"  # on the create reply
    aid = created["id"]

    _advance(client, auth, order, aid, "picked_up")
    delivered = _advance(
        client, auth, order, aid, "delivered"
    ).get_json()["delivery_assignment"]
    assert delivered["driver_phone"] == "+961 3 111 222"

    assert (
        _get(client, auth, order.store.owner, aid)["driver_phone"]
        == "+961 3 111 222"
    )


def test_a_stranger_still_cannot_see_the_assignment_at_all(
    client, auth, make_order, make_user
):
    order = make_order(status="processing")
    aid = _assign(client, auth, order).get_json()["delivery_assignment"]["id"]

    stranger = make_user("customer", email="delivery-stranger@test.local")
    resp = client.get(
        f"/api/delivery/assignments/{aid}", headers=auth(stranger)
    )
    assert resp.status_code == 403


# --------------------------------------------------------------------------- #
# The service, called directly — the path `flask seed` takes. The routes are
# covered above; these guard the rules a non-HTTP caller relies on.
# --------------------------------------------------------------------------- #

def test_service_walks_the_statuses_and_refuses_to_skip_one(db, make_order):
    order = make_order(status="processing")

    a = delivery_service.assign_driver(order, "Ziad Ayoub", "+961 3 300 001")
    assert a.status == "assigned"
    assert a.delivered_at is None

    with pytest.raises(delivery_service.DeliveryError) as exc:
        delivery_service.advance_status(a, order, "delivered")
    assert exc.value.payload["allowed_next_status"] == "picked_up"

    delivery_service.advance_status(a, order, "picked_up")
    delivery_service.advance_status(a, order, "delivered")
    assert a.delivered_at is not None

    # Delivered is terminal.
    with pytest.raises(delivery_service.DeliveryError):
        delivery_service.advance_status(a, order, "picked_up")


def test_service_refuses_a_second_driver_on_the_same_order(db, make_order):
    order = make_order(status="processing")
    delivery_service.assign_driver(order, "Ziad Ayoub", "+961 3 300 001")

    with pytest.raises(delivery_service.DeliveryError) as exc:
        delivery_service.assign_driver(order, "Hadi Mroueh", "+961 3 300 003")
    assert exc.value.status_code == 409


def test_disclosure_rule_is_the_service_answering_not_the_route(
    db, make_order
):
    order = make_order(status="processing")
    a = delivery_service.assign_driver(order, "Ziad Ayoub", "+961 3 300 001")

    for status in ("assigned", "picked_up"):
        a.status = status
        assert delivery_service.may_disclose_phone(a, is_vendor=False)
        assert delivery_service.may_disclose_phone(a, is_vendor=True)

    a.status = "delivered"
    assert not delivery_service.may_disclose_phone(a, is_vendor=False)
    assert delivery_service.may_disclose_phone(a, is_vendor=True)


# The driver's number used to only have to be non-empty, so "abc" saved --
# on a row that is written once and never updated, and that the customer
# is shown in order to phone the driver. These pin the shared rule from
# app/utils/phone.py to this caller.
@pytest.mark.parametrize(
    "bad",
    [
        "abc",
        "+961 3 abc 222",
        "03 111 222",  # national format, no country code
        "12345",  # too short to be a real number
    ],
)
def test_service_refuses_a_driver_phone_that_is_not_dialable(
    db, make_order, bad
):
    order = make_order(status="processing")

    with pytest.raises(delivery_service.DeliveryError):
        delivery_service.assign_driver(order, "Ziad Ayoub", bad)

    assert DeliveryAssignment.query.filter_by(order_id=order.id).count() == 0


def test_a_national_number_is_refused_with_the_country_code_hint(
    db, make_order
):
    order = make_order(status="processing")

    with pytest.raises(delivery_service.DeliveryError) as exc:
        delivery_service.assign_driver(order, "Ziad Ayoub", "03 111 222")

    assert "country code" in exc.value.payload["error"]


@pytest.mark.parametrize(
    "typed",
    ["+961 3 111 222", "00961-3-111-222", "9613111222"],
)
def test_the_number_is_stored_exactly_as_the_vendor_typed_it(
    db, make_order, typed
):
    """Validated, not rewritten — a person reads this number off a screen."""
    order = make_order(status="processing")

    a = delivery_service.assign_driver(order, "Ziad Ayoub", typed)

    assert a.driver_phone == typed


def test_the_route_reports_a_bad_driver_phone_as_a_400(
    client, auth, make_order
):
    order = make_order(status="processing")

    res = client.post(
        "/api/delivery/assignments",
        json={
            "order_id": order.id,
            "driver_name": "Karim Aoun",
            "driver_phone": "abc",
        },
        headers=auth(order.store.owner),
    )

    assert res.status_code == 400
    assert DeliveryAssignment.query.filter_by(order_id=order.id).count() == 0
