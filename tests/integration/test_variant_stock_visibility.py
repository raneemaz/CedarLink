"""The grid card and the "in stock" filter read the variants, not the column.

ADR 0035 says that once a product has variants, ``products.stock`` stops
being consulted for purchasing it. The card and the listing filter went on
reading the column, so a product whose stock had moved onto its variants
showed 0 and was hidden by "in stock only" while its units sat behind the
option picker, ready to sell.
"""

from app.extensions import db

URL = "/api/products"


def _card(response, name):
    for product in response.get_json()["products"]:
        if product["name_en"] == name:
            return product
    return None


def test_the_card_totals_the_active_variants(
    client, make_store, make_product, make_variant
):
    store = make_store()
    product = make_product(store=store, name="Oil", stock=0)
    make_variant(product, label="1L", stock=18)
    make_variant(product, label="2L", stock=12)
    db.session.commit()

    assert _card(client.get(URL), "Oil")["stock"] == 30


def test_a_retired_variant_is_not_counted(
    client, make_store, make_product, make_variant
):
    store = make_store()
    product = make_product(store=store, name="Oil", stock=99)
    make_variant(product, label="1L", stock=18)
    make_variant(product, label="Discontinued", stock=500, is_active=False)
    db.session.commit()

    assert _card(client.get(URL), "Oil")["stock"] == 18


def test_a_product_without_variants_still_shows_its_own_column(
    client, make_store, make_product
):
    store = make_store()
    make_product(store=store, name="Zaatar", stock=40)
    db.session.commit()

    assert _card(client.get(URL), "Zaatar")["stock"] == 40


def test_in_stock_only_keeps_a_product_whose_stock_is_on_its_variants(
    client, make_store, make_product, make_variant
):
    """The bug in one test: sellable, but the column says 0."""
    store = make_store()
    product = make_product(store=store, name="Oil", stock=0)
    make_variant(product, label="1L", stock=30)
    db.session.commit()

    res = client.get(URL, query_string={"in_stock": "true"})

    assert _card(res, "Oil") is not None


def test_in_stock_only_drops_a_product_whose_variants_are_all_empty(
    client, make_store, make_product, make_variant
):
    """And the other direction: the column lies the optimistic way too."""
    store = make_store()
    product = make_product(store=store, name="Scarf", stock=20)
    make_variant(product, label="Blue", stock=0)
    make_variant(product, label="Green", stock=0)
    db.session.commit()

    res = client.get(URL, query_string={"in_stock": "true"})

    assert _card(res, "Scarf") is None


def test_all_variants_retired_falls_back_to_the_product_column(
    client, make_store, make_product, make_variant
):
    """Retiring every variant makes it a plain product again.

    ``select_variant_for_cart`` allows a plain add once no active variant
    remains, and then checks ``products.stock`` — so the card and the
    filter have to fall back to the same column, or the listing would
    hide something the cart is willing to sell.
    """
    store = make_store()
    product = make_product(store=store, name="Scarf", stock=20)
    make_variant(product, label="Blue", stock=7, is_active=False)
    db.session.commit()

    assert _card(client.get(URL), "Scarf")["stock"] == 20

    res = client.get(URL, query_string={"in_stock": "true"})

    assert _card(res, "Scarf") is not None
