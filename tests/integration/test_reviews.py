"""Reviews & ratings (C.3) — verified-purchase gate, the two unique
constraints, the CHECK, and the recompute-not-increment rating aggregate.
"""

from decimal import Decimal

import pytest
from sqlalchemy.exc import IntegrityError

from app.extensions import db
from app.models.product import Product
from app.models.review import Review
from app.models.store import Store
from app.services import review_service


def _post_review(client, auth, user, order, *, rating=5, **body):
    payload = {"order_id": order.id, "rating": rating, **body}
    return client.post("/api/reviews", json=payload, headers=auth(user))


def _delivered_order(make_order, **kw):
    return make_order(status="delivered", **kw)


# --------------------------------------------------------------------------- #
# The verified-purchase gate
# --------------------------------------------------------------------------- #

def test_delivered_order_allows_a_product_review(
    client, auth, make_order, make_product
):
    product = make_product()
    order = _delivered_order(make_order, product=product)

    resp = _post_review(
        client, auth, order.user, order, rating=4,
        product_id=product.id, title="Great", body="Fresh and fast.",
    )

    assert resp.status_code == 201
    review = resp.get_json()["review"]
    assert review["rating"] == 4
    assert review["product_id"] == product.id
    assert review["store_id"] is None


def test_pending_order_cannot_be_reviewed(
    client, auth, make_order, make_product
):
    product = make_product()
    order = make_order(status="pending", product=product)

    resp = _post_review(
        client, auth, order.user, order, product_id=product.id
    )
    assert resp.status_code == 400
    assert resp.get_json()["code"] == "order_not_delivered"


def test_cannot_review_another_users_order(
    client, auth, make_order, make_product, make_user
):
    product = make_product()
    order = _delivered_order(make_order, product=product)
    intruder = make_user("customer", email="intruder-rev@test.local")

    resp = _post_review(
        client, auth, intruder, order, product_id=product.id
    )
    assert resp.status_code == 403
    assert resp.get_json()["code"] == "not_your_order"


def test_cannot_review_a_product_not_in_the_order(
    client, auth, make_order, make_product
):
    bought = make_product()
    other = make_product(store=bought.store)
    order = _delivered_order(make_order, product=bought)

    resp = _post_review(
        client, auth, order.user, order, product_id=other.id
    )
    assert resp.status_code == 400
    assert resp.get_json()["code"] == "product_not_in_order"


def test_store_review_requires_the_order_to_be_from_that_store(
    client, auth, make_order, make_product, make_store
):
    order = _delivered_order(make_order)
    other_store = make_store()

    resp = _post_review(
        client, auth, order.user, order, store_id=other_store.id
    )
    assert resp.status_code == 400
    assert resp.get_json()["code"] == "store_not_in_order"


# --------------------------------------------------------------------------- #
# One review per (user, order, target) — needs BOTH unique constraints
# --------------------------------------------------------------------------- #

def test_second_product_review_on_the_same_order_is_rejected(
    client, auth, make_order, make_product
):
    product = make_product()
    order = _delivered_order(make_order, product=product)

    assert _post_review(
        client, auth, order.user, order, product_id=product.id
    ).status_code == 201
    dup = _post_review(
        client, auth, order.user, order, product_id=product.id
    )
    assert dup.status_code == 409
    assert dup.get_json()["code"] == "already_reviewed"


def test_second_store_review_on_the_same_order_is_rejected(
    client, auth, make_order
):
    """The one a single (user, order, product_id) unique index misses:
    both rows have product_id NULL, and NULL != NULL."""
    order = _delivered_order(make_order)

    assert _post_review(
        client, auth, order.user, order, store_id=order.store_id
    ).status_code == 201
    dup = _post_review(
        client, auth, order.user, order, store_id=order.store_id
    )
    assert dup.status_code == 409
    assert dup.get_json()["code"] == "already_reviewed"


def test_a_product_and_a_store_review_on_one_order_coexist(
    client, auth, make_order, make_product
):
    product = make_product()
    order = _delivered_order(make_order, product=product)

    assert _post_review(
        client, auth, order.user, order, product_id=product.id
    ).status_code == 201
    assert _post_review(
        client, auth, order.user, order, store_id=order.store_id
    ).status_code == 201


# --------------------------------------------------------------------------- #
# Rating and target validation
# --------------------------------------------------------------------------- #

@pytest.mark.parametrize("bad_rating", [0, 6, -1, 100])
def test_rating_out_of_range_is_rejected(
    client, auth, make_order, make_product, bad_rating
):
    product = make_product()
    order = _delivered_order(make_order, product=product)

    resp = _post_review(
        client, auth, order.user, order,
        rating=bad_rating, product_id=product.id,
    )
    assert resp.status_code == 400
    assert resp.get_json()["code"] == "invalid_rating"


def test_review_with_both_targets_is_rejected_by_the_api(
    client, auth, make_order, make_product
):
    product = make_product()
    order = _delivered_order(make_order, product=product)

    resp = _post_review(
        client, auth, order.user, order,
        product_id=product.id, store_id=order.store_id,
    )
    assert resp.status_code == 400
    assert resp.get_json()["code"] == "invalid_target"


def test_review_with_no_target_is_rejected_by_the_api(
    client, auth, make_order
):
    order = _delivered_order(make_order)
    resp = _post_review(client, auth, order.user, order)
    assert resp.status_code == 400
    assert resp.get_json()["code"] == "invalid_target"


def test_check_constraint_rejects_both_targets(db, make_order, make_product):
    product = make_product()
    order = make_order(status="delivered", product=product)

    db.session.add(Review(
        user_id=order.user_id, order_id=order.id,
        product_id=product.id, store_id=order.store_id, rating=5,
    ))
    with pytest.raises(IntegrityError):
        db.session.flush()
    db.session.rollback()


def test_check_constraint_rejects_neither_target(db, make_order):
    order = make_order(status="delivered")

    db.session.add(Review(
        user_id=order.user_id, order_id=order.id,
        product_id=None, store_id=None, rating=5,
    ))
    with pytest.raises(IntegrityError):
        db.session.flush()
    db.session.rollback()


def test_check_constraint_rejects_rating_zero_at_the_db(db, make_order):
    order = make_order(status="delivered")

    db.session.add(Review(
        user_id=order.user_id, order_id=order.id,
        store_id=order.store_id, rating=0,
    ))
    with pytest.raises(IntegrityError):
        db.session.flush()
    db.session.rollback()


# --------------------------------------------------------------------------- #
# Rating aggregate — recomputed, never incremented
# --------------------------------------------------------------------------- #

def _reget_product(pid):
    db.session.expire_all()
    return db.session.get(Product, pid)


def test_product_rating_avg_tracks_create_edit_delete_and_status(
    client, auth, make_order, make_product, make_user
):
    product = make_product()
    buyer_a = make_user("customer", email="rater-a@test.local")
    buyer_b = make_user("customer", email="rater-b@test.local")
    order_a = _delivered_order(make_order, product=product, customer=buyer_a)
    order_b = _delivered_order(make_order, product=product, customer=buyer_b)

    r1 = _post_review(
        client, auth, buyer_a, order_a, rating=4, product_id=product.id
    ).get_json()["review"]
    assert _reget_product(product.id).rating_avg == Decimal("4.00")
    assert _reget_product(product.id).rating_count == 1

    _post_review(
        client, auth, buyer_b, order_b, rating=2, product_id=product.id
    )
    assert _reget_product(product.id).rating_avg == Decimal("3.00")
    assert _reget_product(product.id).rating_count == 2

    # Edit r1 4 -> 5  =>  (5 + 2) / 2 = 3.50
    edit = client.put(
        f"/api/reviews/{r1['id']}", json={"rating": 5}, headers=auth(buyer_a)
    )
    assert edit.status_code == 200
    assert _reget_product(product.id).rating_avg == Decimal("3.50")

    # Delete r1  =>  only the rating-2 review remains
    assert client.delete(
        f"/api/reviews/{r1['id']}", headers=auth(buyer_a)
    ).status_code == 200
    assert _reget_product(product.id).rating_avg == Decimal("2.00")
    assert _reget_product(product.id).rating_count == 1

    # Moderating the last one out drops the average to nothing
    last = Review.query.filter_by(product_id=product.id).one()
    review_service.set_review_status(last.id, "removed")
    db.session.commit()
    assert _reget_product(product.id).rating_avg is None
    assert _reget_product(product.id).rating_count == 0


def test_store_rating_avg_updates_on_review(
    client, auth, make_order, make_user
):
    order = _delivered_order(make_order)
    store_id = order.store_id

    _post_review(client, auth, order.user, order, rating=5, store_id=store_id)

    db.session.expire_all()
    store = db.session.get(Store, store_id)
    assert store.rating_avg == Decimal("5.00")
    assert store.rating_count == 1


# --------------------------------------------------------------------------- #
# Author-only edit / delete
# --------------------------------------------------------------------------- #

def test_non_author_cannot_edit_or_delete(
    client, auth, make_order, make_product, make_user
):
    product = make_product()
    order = _delivered_order(make_order, product=product)
    rid = _post_review(
        client, auth, order.user, order, product_id=product.id
    ).get_json()["review"]["id"]

    stranger = make_user("customer", email="stranger-rev@test.local")

    assert client.put(
        f"/api/reviews/{rid}", json={"rating": 1}, headers=auth(stranger)
    ).status_code == 403
    assert client.delete(
        f"/api/reviews/{rid}", headers=auth(stranger)
    ).status_code == 403


# --------------------------------------------------------------------------- #
# Reads
# --------------------------------------------------------------------------- #

def test_public_list_shows_published_only_newest_first(
    client, auth, make_order, make_product, make_user
):
    product = make_product()
    reviews = []
    for i in range(3):
        buyer = make_user("customer", email=f"list-rev-{i}@test.local")
        order = _delivered_order(make_order, product=product, customer=buyer)
        reviews.append(_post_review(
            client, auth, buyer, order, rating=i + 3, product_id=product.id,
            title=f"r{i}",
        ).get_json()["review"])

    review_service.set_review_status(reviews[0]["id"], "removed")
    db.session.commit()

    body = client.get(
        f"/api/products/{product.id}/reviews"
    ).get_json()
    titles = [r["title"] for r in body["reviews"]]
    assert titles == ["r2", "r1"]  # newest first, removed one gone
    assert body["total"] == 2


def test_order_reviewable_reports_what_is_left(
    client, auth, make_order, make_product
):
    product = make_product()
    order = _delivered_order(make_order, product=product)

    before = client.get(
        f"/api/orders/{order.id}/reviewable", headers=auth(order.user)
    ).get_json()
    assert before["can_review"] is True
    assert before["store"]["already_reviewed"] is False
    assert before["products"][0]["already_reviewed"] is False

    _post_review(client, auth, order.user, order, product_id=product.id)

    after = client.get(
        f"/api/orders/{order.id}/reviewable", headers=auth(order.user)
    ).get_json()
    assert after["products"][0]["already_reviewed"] is True
    assert after["store"]["already_reviewed"] is False


def test_product_payload_carries_rating_fields(
    client, auth, make_order, make_product
):
    product = make_product()
    order = _delivered_order(make_order, product=product)
    _post_review(
        client, auth, order.user, order, rating=4, product_id=product.id
    )

    detail = client.get(f"/api/products/{product.id}").get_json()
    assert detail["rating_avg"] == 4.0
    assert detail["rating_count"] == 1
