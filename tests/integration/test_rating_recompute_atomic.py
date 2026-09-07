"""review_service._recalculate_rating emits exactly one SQL statement.

This proves the *shape* is race-safe, not that a race was reproduced.
SQLite serialises writers, so it cannot exhibit the lost-update this
guards against (two writers, both read the pre-commit count, both write,
second stores a stale value). The guarantee is that the recompute is now
a single `UPDATE products SET rating_count = (SELECT …), rating_avg =
(SELECT …) WHERE id = :id` — one atomic statement — so the same code
ports to Postgres unchanged (ADR 0032 §4, ADR 0015).
"""

from sqlalchemy import event

from app.extensions import db
from app.models.product import Product
from app.services import review_service


def _count_statements(fn, *warm):
    """Run ``fn`` and return the SQL it emitted. ``warm`` objects are
    touched first so a lazy attribute reload does not land inside the
    measured window (in real use the recompute runs mid-transaction, with
    the entity already loaded)."""
    for obj in warm:
        _ = obj.id

    seen = []

    def _on(conn, cursor, statement, params, context, many):
        seen.append(statement)

    engine = db.engine
    event.listen(engine, "before_cursor_execute", _on)
    try:
        fn()
    finally:
        event.remove(engine, "before_cursor_execute", _on)
    return seen


def test_product_recompute_is_one_statement(
    make_product, make_user, make_order
):
    product = make_product(stock=5)
    buyer = make_user("customer", email="atomic-p@test.local")
    order = make_order(customer=buyer, product=product, status="delivered")
    review_service.create_review(
        buyer, order.id, {"product_id": product.id}, 4, "t", "body"
    )
    db.session.commit()

    statements = _count_statements(
        lambda: review_service._recalculate_rating("product", product),
        product,
    )

    assert len(statements) == 1, statements
    sql = statements[0].lower()
    assert sql.startswith("update products")
    assert sql.count("select") == 2  # count() and round(avg())


def test_store_recompute_is_one_statement(
    make_store, make_product, make_user, make_order
):
    store = make_store()
    product = make_product(store=store, stock=5)
    buyer = make_user("customer", email="atomic-s@test.local")
    order = make_order(customer=buyer, product=product, status="delivered")
    review_service.create_review(
        buyer, order.id, {"store_id": store.id}, 5, "t", "body"
    )
    db.session.commit()

    statements = _count_statements(
        lambda: review_service._recalculate_rating("store", store),
        store,
    )

    assert len(statements) == 1, statements
    assert statements[0].lower().startswith("update stores")


def test_the_recompute_still_produces_the_right_numbers(
    make_product, make_user, make_order
):
    """Control: one statement, and it is the correct one."""
    product = make_product(stock=5)
    for rating in (5, 4, 3):
        buyer = make_user("customer", email=f"n{rating}@test.local")
        order = make_order(
            customer=buyer, product=product, status="delivered"
        )
        review_service.create_review(
            buyer, order.id, {"product_id": product.id}, rating, "t", "body"
        )
    db.session.commit()
    db.session.expire_all()

    fresh = db.session.get(Product, product.id)
    assert fresh.rating_count == 3
    assert float(fresh.rating_avg) == 4.0  # (5+4+3)/3
