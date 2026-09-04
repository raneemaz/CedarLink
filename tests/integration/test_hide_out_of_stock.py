"""The "hide sold-out products" preference, honoured by the listing.

It was storable and editable for a while before anything read it — a
control the customer could toggle that changed nothing. These tests are
what stops that being true again.
"""

from app.extensions import db
from app.services import shopping_preferences_service as svc

URL = "/api/products"


def _names(response):
    return sorted(p["name_en"] for p in response.get_json()["products"])


def _set_hide(user, value):
    prefs = svc.get_or_create_preferences(user.id)
    ok, error = svc.apply_preference_updates(
        prefs, {"hide_out_of_stock": value}
    )
    assert ok, error
    db.session.commit()


def _catalogue(make_store, make_product):
    store = make_store()
    make_product(store=store, name="InStock", stock=5)
    make_product(store=store, name="SoldOut", stock=0)
    return store


def test_the_preference_hides_sold_out_products(
    client, auth, customer, make_store, make_product
):
    _catalogue(make_store, make_product)

    assert _names(client.get(URL, headers=auth(customer))) == [
        "InStock", "SoldOut"
    ]

    _set_hide(customer, True)

    assert _names(client.get(URL, headers=auth(customer))) == ["InStock"]


def test_turning_the_preference_back_off_restores_them(
    client, auth, customer, make_store, make_product
):
    _catalogue(make_store, make_product)
    _set_hide(customer, True)
    _set_hide(customer, False)

    assert _names(client.get(URL, headers=auth(customer))) == [
        "InStock", "SoldOut"
    ]


def test_a_signed_out_visitor_is_unaffected(
    client, make_store, make_product
):
    _catalogue(make_store, make_product)

    assert _names(client.get(URL)) == ["InStock", "SoldOut"]


def test_an_explicit_in_stock_false_overrides_the_preference(
    client, auth, customer, make_store, make_product
):
    """The request the customer is making now beats the standing one."""
    _catalogue(make_store, make_product)
    _set_hide(customer, True)

    shown = client.get(
        URL, query_string={"in_stock": "false"}, headers=auth(customer)
    )
    assert _names(shown) == ["InStock", "SoldOut"]


def test_an_explicit_in_stock_true_still_filters_without_the_preference(
    client, auth, customer, make_store, make_product
):
    _catalogue(make_store, make_product)

    filtered = client.get(
        URL, query_string={"in_stock": "true"}, headers=auth(customer)
    )
    assert _names(filtered) == ["InStock"]


def test_a_vendor_still_sees_their_own_sold_out_stock(
    client, auth, make_user, make_store, make_product
):
    """A vendor needs the whole picture of their own shelf."""
    owner = make_user("vendor", email="hoos-vendor@test.local")
    store = make_store(owner=owner)
    make_product(store=store, name="InStock", stock=5)
    make_product(store=store, name="SoldOut", stock=0)

    prefs = svc.get_or_create_preferences(owner.id)
    ok, _ = svc.apply_preference_updates(prefs, {"hide_out_of_stock": True})
    assert ok
    db.session.commit()

    listed = client.get(
        URL, query_string={"store_id": store.id}, headers=auth(owner)
    )
    assert _names(listed) == ["InStock", "SoldOut"]


def test_the_listing_does_not_create_a_preferences_row(
    client, auth, customer, make_store, make_product
):
    _catalogue(make_store, make_product)

    client.get(URL, headers=auth(customer))

    from app.models.shopping_preferences import ShoppingPreferences

    assert ShoppingPreferences.query.count() == 0, (
        "a GET must not write"
    )
