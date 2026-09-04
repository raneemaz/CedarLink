"""GET /api/home/sections — the home page in interest order.

Signed out and signed in take the same path; the only difference is
whether anyone has stated an interest. Nothing here depends on browsing
history, because none is recorded.
"""

from app.extensions import db
from app.services import shopping_preferences_service as svc

URL = "/api/home/sections"


def _order(body):
    return [s["category"]["name_en"] for s in body["sections"]]


def _set_interests(user, category_ids):
    prefs = svc.get_or_create_preferences(user.id)
    ok, error = svc.apply_preference_updates(
        prefs, {"interest_category_ids": category_ids}
    )
    assert ok, error
    db.session.commit()


def test_a_signed_out_visitor_gets_the_default_order(
    client, make_category, make_store, make_product
):
    store = make_store()
    busy, quiet = make_category("Busy"), make_category("Quiet")
    for _ in range(3):
        make_product(store=store, category=busy)
    make_product(store=store, category=quiet)

    response = client.get(URL)
    assert response.status_code == 200

    body = response.get_json()
    assert _order(body) == ["Busy", "Quiet"]
    assert body["personalized"] is False


def test_stated_interests_lead_the_page(
    client, auth, customer, make_category, make_store, make_product
):
    store = make_store()
    busy = make_category("Busy")
    for _ in range(4):
        make_product(store=store, category=busy)

    chosen = make_category("Chosen")
    make_product(store=store, category=chosen)

    _set_interests(customer, [chosen.id])

    body = client.get(URL, headers=auth(customer)).get_json()

    assert _order(body)[0] == "Chosen"
    assert "Busy" in _order(body)
    assert body["personalized"] is True


def test_a_customer_with_no_interests_gets_the_default_order(
    client, auth, customer, make_category, make_store, make_product
):
    store = make_store()
    busy, quiet = make_category("Busy"), make_category("Quiet")
    for _ in range(2):
        make_product(store=store, category=busy)
    make_product(store=store, category=quiet)

    body = client.get(URL, headers=auth(customer)).get_json()

    assert _order(body) == ["Busy", "Quiet"]
    assert body["personalized"] is False


def test_empty_categories_are_not_shown(
    client, make_category, make_store, make_product
):
    store = make_store()
    stocked = make_category("Stocked")
    make_category("Bare")
    make_product(store=store, category=stocked)

    assert _order(client.get(URL).get_json()) == ["Stocked"]


def test_products_from_a_hidden_store_do_not_appear(
    client, make_category, make_store, make_product
):
    category = make_category("Only")
    hidden = make_store(approval_status="pending")
    make_product(store=hidden, category=category)

    # The store is not approved, so its product cannot carry the section.
    assert client.get(URL).get_json()["sections"] == []


def test_a_section_carries_the_product_card_shape(
    client, make_category, make_store, make_product
):
    store = make_store()
    category = make_category("Only")
    make_product(store=store, category=category, price=12.5, stock=7)

    section = client.get(URL).get_json()["sections"][0]
    product = section["products"][0]

    # Same keys the product grid already renders, because both endpoints
    # build the card with one function.
    for key in (
        "id", "price", "stock", "store_id", "store_name", "category_id",
        "image", "name_en", "name_ar", "name_fr", "rating_avg",
        "rating_count",
    ):
        assert key in product, f"missing {key}"

    assert product["price"] == 12.5
    assert product["stock"] == 7
    assert section["category"]["display_name"] == "Only"


def test_the_section_list_is_capped(
    client, make_category, make_store, make_product
):
    store = make_store()
    for n in range(svc.MAX_INTERESTS + 4):
        make_product(store=store, category=make_category(f"C{n:02d}"))

    from app.services import home_service

    sections = client.get(URL).get_json()["sections"]
    assert len(sections) == home_service.MAX_SECTIONS


def test_requesting_sections_does_not_create_a_preferences_row(
    client, auth, customer, make_category, make_store, make_product
):
    make_product(store=make_store(), category=make_category("Only"))

    client.get(URL, headers=auth(customer))

    from app.models.shopping_preferences import ShoppingPreferences

    assert ShoppingPreferences.query.count() == 0


def test_interests_round_trip_through_the_preferences_endpoint(
    client, auth, customer, make_category
):
    first, second = make_category("First"), make_category("Second")
    url = f"/api/users/{customer.id}/shopping-preferences"

    saved = client.put(
        url,
        json={"interest_category_ids": [second.id, first.id]},
        headers=auth(customer),
    )
    assert saved.status_code == 200

    read = client.get(url, headers=auth(customer)).get_json()
    assert read["shopping_preferences"]["interest_category_ids"] == [
        second.id, first.id
    ]


def test_too_many_interests_are_refused_by_the_endpoint(
    client, auth, customer, make_category
):
    categories = [
        make_category(f"C{n}") for n in range(svc.MAX_INTERESTS + 1)
    ]

    response = client.put(
        f"/api/users/{customer.id}/shopping-preferences",
        json={"interest_category_ids": [c.id for c in categories]},
        headers=auth(customer),
    )
    assert response.status_code == 400


def test_another_customer_cannot_set_your_interests(
    client, auth, customer, make_user, make_category
):
    stranger = make_user("customer", email="interest-stranger@test.local")

    response = client.put(
        f"/api/users/{customer.id}/shopping-preferences",
        json={"interest_category_ids": [make_category("A").id]},
        headers=auth(stranger),
    )
    assert response.status_code == 403
