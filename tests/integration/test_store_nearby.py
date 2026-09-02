"""Location data + distance search (C.2).

Centre for every search is a fixed point in Beirut. Stores are placed by
offsetting from it in km, converting km -> degrees with the SAME constants
the service uses, so the assertions are about the algorithm, not about
whether two people rounded the earth's radius the same way.
"""

import math

from app.extensions import db
from app.models.store import Store
from app.utils.geo import KM_PER_DEG_LAT

CENTER_LAT = 33.8900
CENTER_LNG = 35.5000
KM_PER_DEG_LNG = KM_PER_DEG_LAT * math.cos(math.radians(CENTER_LAT))


def _north(km):
    return CENTER_LAT + km / KM_PER_DEG_LAT


def _east(km):
    return CENTER_LNG + km / KM_PER_DEG_LNG


def _search(client, radius, lat=CENTER_LAT, lng=CENTER_LNG, extra=""):
    resp = client.get(
        f"/api/stores?near={lat},{lng}&radius={radius}&limit=50{extra}"
    )
    assert resp.status_code == 200, resp.get_json()
    return resp.get_json()


# --------------------------------------------------------------------------- #
# nearby()
# --------------------------------------------------------------------------- #

def test_store_inside_radius_is_returned_one_outside_is_not(
    client, make_store
):
    make_store(name="Near", latitude=_north(2), longitude=CENTER_LNG)
    make_store(name="Far", latitude=_north(30), longitude=CENTER_LNG)

    body = _search(client, radius=10)
    names = [s["name"] for s in body["stores"]]

    assert "Near" in names and "Far" not in names
    assert body["total"] == 1
    assert abs(body["stores"][0]["distance_km"] - 2.0) < 0.15


def test_results_are_ordered_by_true_distance(client, make_store):
    make_store(name="5km", latitude=_north(5), longitude=CENTER_LNG)
    make_store(name="1km", latitude=_north(1), longitude=CENTER_LNG)
    make_store(name="3km", latitude=_north(3), longitude=CENTER_LNG)

    names = [s["name"] for s in _search(client, radius=10)["stores"]]
    assert names == ["1km", "3km", "5km"]


def test_a_store_with_no_coordinates_never_appears_in_a_distance_search(
    client, make_store
):
    make_store(name="No pin", latitude=None, longitude=None)
    make_store(name="Pinned", latitude=CENTER_LAT, longitude=CENTER_LNG)

    names = [s["name"] for s in _search(client, radius=90)["stores"]]
    assert names == ["Pinned"]  # the coordless store is not sorted as (0, 0)


def test_an_online_only_store_never_appears_in_a_distance_search(
    client, make_store
):
    # Even with coordinates on the row (a data inconsistency), the flag wins.
    make_store(
        name="Online", latitude=CENTER_LAT, longitude=CENTER_LNG,
        is_online_only=True,
    )
    make_store(name="Physical", latitude=CENTER_LAT, longitude=CENTER_LNG)

    names = [s["name"] for s in _search(client, radius=10)["stores"]]
    assert names == ["Physical"]


def test_bounding_box_keeps_a_store_due_east_or_west_at_the_radius_edge(
    client, make_store
):
    """The regression test for the longitude scaling.

    A store 9.2 km due east sits at ~0.92 x radius, which is inside the
    true circle but OUTSIDE a box whose east-west half-width was computed
    with 111 km/deg flat (0.92 > cos(33.89 deg) = 0.83). It must still be
    returned; if this fails the box is scaling longitude by 111 instead of
    111 * cos(lat).
    """
    make_store(name="Due east", latitude=CENTER_LAT, longitude=_east(9.2))
    make_store(name="Due west", latitude=CENTER_LAT, longitude=_east(-9.2))
    make_store(name="Too far east", latitude=CENTER_LAT, longitude=_east(12))

    names = {s["name"] for s in _search(client, radius=10)["stores"]}
    assert names == {"Due east", "Due west"}


# --------------------------------------------------------------------------- #
# PUT /api/stores/{id}/location
# --------------------------------------------------------------------------- #

def test_set_location_happy_path_and_clear(client, auth, store):
    headers = auth(store.owner)
    url = f"/api/stores/{store.id}/location"

    ok = client.put(
        url, json={"latitude": 33.893800, "longitude": 35.501800},
        headers=headers,
    )
    assert ok.status_code == 200
    body = ok.get_json()["store"]
    assert body["latitude"] == 33.8938
    assert body["longitude"] == 35.5018

    cleared = client.put(
        url, json={"latitude": None, "longitude": None}, headers=headers
    )
    assert cleared.status_code == 200
    assert cleared.get_json()["store"]["latitude"] is None


def test_set_location_rejects_out_of_range_and_non_numeric(
    client, auth, store
):
    headers = auth(store.owner)
    url = f"/api/stores/{store.id}/location"
    for payload in (
        {"latitude": 91, "longitude": 35.5},
        {"latitude": -90.1, "longitude": 35.5},
        {"latitude": 33.9, "longitude": 181},
        {"latitude": 33.9, "longitude": "east a bit"},
        {"latitude": True, "longitude": 35.5},
    ):
        resp = client.put(url, json=payload, headers=headers)
        assert resp.status_code == 400, payload


def test_set_location_rejects_one_coordinate_without_the_other(
    client, auth, store
):
    headers = auth(store.owner)
    url = f"/api/stores/{store.id}/location"
    assert client.put(
        url, json={"latitude": 33.9}, headers=headers
    ).status_code == 400
    assert client.put(
        url, json={"longitude": 35.5}, headers=headers
    ).status_code == 400


def test_non_owner_cannot_set_a_stores_location(
    client, auth, store, make_user
):
    intruder = make_user("vendor", email="loc-intruder@test.local")
    resp = client.put(
        f"/api/stores/{store.id}/location",
        json={"latitude": 33.9, "longitude": 35.5},
        headers=auth(intruder),
    )
    assert resp.status_code == 403


# --------------------------------------------------------------------------- #
# is_online_only
# --------------------------------------------------------------------------- #

def test_setting_online_only_clears_the_map_pin(client, auth, store):
    headers = auth(store.owner)
    client.put(
        f"/api/stores/{store.id}/location",
        json={"latitude": 33.89, "longitude": 35.50},
        headers=headers,
    )

    resp = client.put(
        f"/api/stores/{store.id}",
        json={"is_online_only": True},
        headers=headers,
    )
    assert resp.status_code == 200
    body = resp.get_json()["store"]
    assert body["is_online_only"] is True
    assert body["latitude"] is None and body["longitude"] is None

    db.session.expire_all()
    assert db.session.get(Store, store.id).latitude is None

    # and a pin cannot be set back while it stays online-only
    refused = client.put(
        f"/api/stores/{store.id}/location",
        json={"latitude": 33.89, "longitude": 35.50},
        headers=headers,
    )
    assert refused.status_code == 400


# --------------------------------------------------------------------------- #
# The plain directory is untouched
# --------------------------------------------------------------------------- #

def test_directory_without_near_behaves_exactly_as_before(client, make_store):
    for i in range(3):
        make_store(
            name=f"S{i}", latitude=CENTER_LAT, longitude=CENTER_LNG
        )

    by_name = client.get("/api/stores?sort=name").get_json()
    assert [s["name"] for s in by_name["stores"]] == ["S0", "S1", "S2"]
    assert "distance_km" not in by_name["stores"][0]

    by_newest = client.get("/api/stores?sort=newest").get_json()
    assert [s["name"] for s in by_newest["stores"]] == ["S2", "S1", "S0"]

    # coordinates ARE in the payload now, distance_km is not
    assert by_name["stores"][0]["latitude"] == CENTER_LAT


def test_near_with_bad_input_is_a_400(client, make_store):
    make_store(latitude=CENTER_LAT, longitude=CENTER_LNG)
    assert client.get("/api/stores?near=33.89").status_code == 400
    assert client.get("/api/stores?near=abc,def").status_code == 400
    assert client.get(
        f"/api/stores?near={CENTER_LAT},{CENTER_LNG}&radius=-1"
    ).status_code == 400
    assert client.get(
        f"/api/stores?near={CENTER_LAT},{CENTER_LNG}&radius=huge"
    ).status_code == 400
