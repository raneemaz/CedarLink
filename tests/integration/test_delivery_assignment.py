"""Delivery assignments — the driver's phone is a scoped disclosure, not a
field in the dump (docs/decisions/0019)."""

from app.models.delivery_assignment import DeliveryAssignment


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
