"""shopping_preferences_service — validation, interests, and home order.

The service had no tests at all before this file, so it covers the
pre-existing checkout preferences as well as the interests added with
them: a whitelist validator is only worth having if something proves it
rejects what it claims to.

The property that matters most here is that ranking is *stated*, never
inferred. Nothing in these tests sets up a purchase, a view, or a search
to influence an order, because nothing in the service reads one.
"""

import pytest

from app.extensions import db
from app.models.shopping_interest import ShoppingInterest
from app.models.shopping_preferences import ShoppingPreferences
from app.services import shopping_preferences_service as svc


@pytest.fixture()
def prefs(customer):
    return svc.get_or_create_preferences(customer.id)


def _apply(prefs, data):
    ok, error = svc.apply_preference_updates(prefs, data)
    if ok:
        db.session.commit()
    return ok, error


# --------------------------------------------------------------------------- #
# The row itself
# --------------------------------------------------------------------------- #

def test_preferences_are_created_once_with_defaults(customer):
    first = svc.get_or_create_preferences(customer.id)

    assert first.autofill_default_address is True
    assert first.preferred_payment_method == "cash_on_delivery"
    assert first.default_delivery_city is None
    assert first.hide_out_of_stock is False
    assert first.interest_category_ids == []

    second = svc.get_or_create_preferences(customer.id)

    assert second.id == first.id
    assert ShoppingPreferences.query.count() == 1


def test_serialize_exposes_exactly_the_editable_keys(prefs):
    assert set(svc.serialize_preferences(prefs)) == svc.PREFERENCE_KEYS


# --------------------------------------------------------------------------- #
# Validation of the pre-existing checkout preferences
# --------------------------------------------------------------------------- #

def test_a_non_object_body_is_refused(prefs):
    ok, error = svc.apply_preference_updates(prefs, ["not", "a", "dict"])
    assert ok is False
    assert "JSON object" in error


def test_unknown_keys_are_refused_and_named(prefs):
    ok, error = svc.apply_preference_updates(
        prefs, {"hide_out_of_stock": True, "make_me_admin": True}
    )
    assert ok is False
    assert "make_me_admin" in error

    # Rejected as a whole — the valid key alongside it is not applied.
    db.session.rollback()
    assert svc.get_or_create_preferences(prefs.user_id).hide_out_of_stock is (
        False
    )


def test_booleans_must_be_booleans(prefs):
    ok, error = svc.apply_preference_updates(
        prefs, {"hide_out_of_stock": "yes"}
    )
    assert ok is False
    assert "hide_out_of_stock" in error


def test_payment_method_is_limited_to_the_known_set(prefs):
    ok, _ = _apply(prefs, {"preferred_payment_method": "card"})
    assert ok is True
    assert prefs.preferred_payment_method == "card"

    ok, error = svc.apply_preference_updates(
        prefs, {"preferred_payment_method": "bitcoin"}
    )
    assert ok is False
    assert "cash_on_delivery" in error


def test_delivery_city_is_trimmed_length_capped_and_clearable(prefs):
    ok, _ = _apply(prefs, {"default_delivery_city": "  Beirut  "})
    assert ok is True
    assert prefs.default_delivery_city == "Beirut"

    ok, _ = _apply(prefs, {"default_delivery_city": ""})
    assert ok is True
    assert prefs.default_delivery_city is None

    ok, error = svc.apply_preference_updates(
        prefs, {"default_delivery_city": "x" * (svc.MAX_CITY_LENGTH + 1)}
    )
    assert ok is False
    assert str(svc.MAX_CITY_LENGTH) in error


def test_only_the_keys_sent_are_touched(prefs):
    _apply(prefs, {"hide_out_of_stock": True, "default_delivery_city": "Tyre"})

    _apply(prefs, {"hide_out_of_stock": False})

    assert prefs.hide_out_of_stock is False
    assert prefs.default_delivery_city == "Tyre", (
        "a partial update must not blank the keys it did not mention"
    )


# --------------------------------------------------------------------------- #
# Interests
# --------------------------------------------------------------------------- #

def test_interests_are_stored_in_the_order_chosen(prefs, make_category):
    third = make_category("Third")
    first = make_category("First")
    second = make_category("Second")

    ok, _ = _apply(
        prefs,
        {"interest_category_ids": [first.id, second.id, third.id]},
    )
    assert ok is True

    # The customer's order, not the ids' order.
    assert prefs.interest_category_ids == [first.id, second.id, third.id]
    assert [i.position for i in prefs.interests] == [0, 1, 2]


def test_sending_the_list_replaces_it_rather_than_merging(
    prefs, make_category
):
    a, b, c = (make_category(n) for n in ("A", "B", "C"))

    _apply(prefs, {"interest_category_ids": [a.id, b.id]})
    _apply(prefs, {"interest_category_ids": [c.id]})

    assert prefs.interest_category_ids == [c.id]


def test_interests_can_be_cleared_entirely(prefs, make_category):
    a = make_category("A")
    _apply(prefs, {"interest_category_ids": [a.id]})

    ok, _ = _apply(prefs, {"interest_category_ids": []})
    assert ok is True
    assert prefs.interest_category_ids == []
    assert ShoppingInterest.query.count() == 0, "the rows go, not just the list"


def test_null_clears_interests(prefs, make_category):
    _apply(prefs, {"interest_category_ids": [make_category("A").id]})

    ok, _ = _apply(prefs, {"interest_category_ids": None})
    assert ok is True
    assert prefs.interest_category_ids == []


def test_more_than_the_maximum_is_refused(prefs, make_category):
    categories = [make_category(f"C{n}") for n in range(svc.MAX_INTERESTS + 1)]

    ok, error = svc.apply_preference_updates(
        prefs, {"interest_category_ids": [c.id for c in categories]}
    )
    assert ok is False
    assert str(svc.MAX_INTERESTS) in error

    # Exactly the maximum is fine.
    db.session.rollback()
    prefs = svc.get_or_create_preferences(prefs.user_id)
    ok, _ = _apply(
        prefs,
        {
            "interest_category_ids": [
                c.id for c in categories[: svc.MAX_INTERESTS]
            ]
        },
    )
    assert ok is True


def test_a_repeated_category_is_refused(prefs, make_category):
    a = make_category("A")

    ok, error = svc.apply_preference_updates(
        prefs, {"interest_category_ids": [a.id, a.id]}
    )
    assert ok is False
    assert "repeat" in error.lower()


def test_an_unknown_category_is_refused_and_named(prefs, make_category):
    a = make_category("A")

    ok, error = svc.apply_preference_updates(
        prefs, {"interest_category_ids": [a.id, 999999]}
    )
    assert ok is False
    assert "999999" in error


@pytest.mark.parametrize("bad", ["1", 1.5, True, None, {"id": 1}])
def test_non_integer_ids_are_refused(prefs, bad):
    ok, error = svc.apply_preference_updates(
        prefs, {"interest_category_ids": [bad]}
    )
    assert ok is False
    assert "category ids" in error


def test_a_non_list_is_refused(prefs):
    ok, error = svc.apply_preference_updates(
        prefs, {"interest_category_ids": 7}
    )
    assert ok is False
    assert "list" in error


def test_deleting_a_category_takes_its_interest_row_with_it(
    prefs, make_category
):
    a, b = make_category("A"), make_category("B")
    _apply(prefs, {"interest_category_ids": [a.id, b.id]})

    db.session.delete(a)
    db.session.commit()
    db.session.expire_all()

    # No dangling id left behind for the home page to trip over.
    assert svc.get_or_create_preferences(
        prefs.user_id
    ).interest_category_ids == [b.id]


# --------------------------------------------------------------------------- #
# Home ordering
# --------------------------------------------------------------------------- #

def _names(categories):
    return [c.name_en for c in categories]


def test_the_default_order_leads_with_the_busiest_category(
    customer, make_category, make_product, make_store
):
    """No stated interest, so the honest guess is where the goods are."""
    store = make_store()
    quiet = make_category("Quiet")
    busy = make_category("Busy")

    for _ in range(3):
        make_product(store=store, category=busy)
    make_product(store=store, category=quiet)

    assert _names(svc.ordered_categories(customer.id))[:2] == [
        "Busy", "Quiet"
    ]


def test_equal_counts_fall_back_to_a_stable_name_order(
    customer, make_category, make_store, make_product
):
    store = make_store()
    for name in ("Zebra", "Apple", "Mango"):
        make_product(store=store, category=make_category(name))

    order = _names(svc.ordered_categories(customer.id))

    assert order == sorted(order), "equal counts must not shuffle"


def test_stated_interests_come_first_in_the_customers_own_order(
    customer, make_category, make_store, make_product
):
    store = make_store()
    busy = make_category("Busy")
    for _ in range(5):
        make_product(store=store, category=busy)

    picked_second = make_category("Alpha")
    picked_first = make_category("Beta")
    make_product(store=store, category=picked_first)
    make_product(store=store, category=picked_second)

    prefs = svc.get_or_create_preferences(customer.id)
    _apply(
        prefs,
        {"interest_category_ids": [picked_first.id, picked_second.id]},
    )

    order = _names(svc.ordered_categories(customer.id))

    # The interests lead, in the order chosen — ahead of the category with
    # five times the stock.
    assert order[:2] == ["Beta", "Alpha"]
    assert "Busy" in order[2:]


def test_an_interest_promotes_a_category_it_never_hides_the_others(
    customer, make_category, make_store, make_product
):
    store = make_store()
    kept = [make_category(n) for n in ("One", "Two", "Three")]
    for category in kept:
        make_product(store=store, category=category)

    prefs = svc.get_or_create_preferences(customer.id)
    _apply(prefs, {"interest_category_ids": [kept[-1].id]})

    order = _names(svc.ordered_categories(customer.id))

    assert order[0] == "Three"
    assert set(order) == {"One", "Two", "Three"}


def test_a_signed_out_visitor_gets_the_default_order(
    make_category, make_store, make_product
):
    store = make_store()
    quiet = make_category("Quiet")
    busy = make_category("Busy")
    for _ in range(2):
        make_product(store=store, category=busy)
    make_product(store=store, category=quiet)

    assert _names(svc.ordered_categories(None))[:2] == ["Busy", "Quiet"]


def test_reading_the_order_never_creates_a_preferences_row(customer):
    svc.ordered_categories(customer.id)
    svc.has_interests(customer.id)

    assert ShoppingPreferences.query.count() == 0, (
        "asking how to sort must not be a write"
    )


def test_has_interests_reports_whether_anything_was_stated(
    customer, make_category
):
    assert svc.has_interests(None) is False
    assert svc.has_interests(customer.id) is False

    prefs = svc.get_or_create_preferences(customer.id)
    assert svc.has_interests(customer.id) is False

    _apply(prefs, {"interest_category_ids": [make_category("A").id]})
    assert svc.has_interests(customer.id) is True
