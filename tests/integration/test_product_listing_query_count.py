"""The product listing does not fan out per row (ADR 0032 F2 / ADR 0033).

`product_card()` reads `product.images[0]` and `product.store.name` for
every row. Without eager loading a page of N products fires ~2N extra
queries. `get_products` now `selectinload`s both, so the query count is
flat regardless of page size.
"""

from sqlalchemy import event

from app.extensions import db


def _count(fn):
    seen = []

    def _on(conn, cursor, statement, params, context, many):
        if statement.lstrip().upper().startswith("SELECT"):
            seen.append(statement)

    event.listen(db.engine, "before_cursor_execute", _on)
    try:
        fn()
    finally:
        event.remove(db.engine, "before_cursor_execute", _on)
    return seen


def _make_catalogue(make_store, make_product, n):
    store = make_store()
    for _ in range(n):
        make_product(store=store, stock=5)
    return store


def test_listing_query_count_is_flat_across_page_size(
    client, make_store, make_product
):
    _make_catalogue(make_store, make_product, 20)

    small = _count(lambda: client.get("/api/products?limit=3"))
    large = _count(lambda: client.get("/api/products?limit=18"))

    # A page of 3 and a page of 18 cost the same number of SELECTs.
    assert len(small) == len(large), (
        f"page of 3: {len(small)} queries, page of 18: {len(large)} — "
        "the listing is fanning out per row"
    )
    # And that number is small: main query + count + images + stores.
    assert len(large) <= 5, large


def test_listing_still_returns_the_right_shape(
    client, make_store, make_product
):
    _make_catalogue(make_store, make_product, 4)
    resp = client.get("/api/products?limit=10")
    assert resp.status_code == 200
    cards = resp.get_json()["products"]
    assert len(cards) == 4
    assert cards[0]["store_name"]
    assert "image" in cards[0]
