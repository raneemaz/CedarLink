"""Review moderation (C.3, item 7c) — report, status transitions, the admin
queue, and what still counts toward a rating at each status.
"""

from decimal import Decimal

from app.extensions import db
from app.models.product import Product
from app.models.review import Review
from app.models.review_report import ReviewReport
from app.services import review_service


def _delivered_order(make_order, **kw):
    return make_order(status="delivered", **kw)


def _review(client, auth, order, product, *, rating=4):
    return client.post(
        "/api/reviews",
        json={"order_id": order.id, "product_id": product.id, "rating": rating},
        headers=auth(order.user),
    ).get_json()["review"]


def _reget(model, pk):
    db.session.expire_all()
    return db.session.get(model, pk)


# --------------------------------------------------------------------------- #
# Report
# --------------------------------------------------------------------------- #

def test_a_report_flags_the_review_and_records_the_reason(
    client, auth, make_order, make_product, make_user
):
    product = make_product()
    order = _delivered_order(make_order, product=product)
    review = _review(client, auth, order, product)

    reporter = make_user("customer", email="reporter@test.local")
    resp = client.post(
        f"/api/reviews/{review['id']}/report",
        json={"reason": "Contains a phone number and spam links"},
        headers=auth(reporter),
    )
    assert resp.status_code == 201

    row = _reget(Review, review["id"])
    assert row.status == "flagged"
    report = ReviewReport.query.filter_by(review_id=review["id"]).one()
    assert report.reason == "Contains a phone number and spam links"
    assert report.user_id == reporter.id


def test_report_requires_a_reason(
    client, auth, make_order, make_product, make_user
):
    product = make_product()
    order = _delivered_order(make_order, product=product)
    review = _review(client, auth, order, product)

    reporter = make_user("customer", email="noreason@test.local")
    for body in ({}, {"reason": "   "}):
        resp = client.post(
            f"/api/reviews/{review['id']}/report",
            json=body,
            headers=auth(reporter),
        )
        assert resp.status_code == 400
        assert resp.get_json()["code"] == "reason_required"


def test_a_user_cannot_report_the_same_review_twice(
    client, auth, make_order, make_product, make_user
):
    product = make_product()
    order = _delivered_order(make_order, product=product)
    review = _review(client, auth, order, product)
    reporter = make_user("customer", email="dbl-report@test.local")

    first = client.post(
        f"/api/reviews/{review['id']}/report",
        json={"reason": "spam"},
        headers=auth(reporter),
    )
    assert first.status_code == 201

    again = client.post(
        f"/api/reviews/{review['id']}/report",
        json={"reason": "still spam"},
        headers=auth(reporter),
    )
    assert again.status_code == 409
    assert again.get_json()["code"] == "already_reported"
    assert ReviewReport.query.filter_by(review_id=review["id"]).count() == 1


def test_a_second_reporter_adds_a_report_without_changing_status(
    client, auth, make_order, make_product, make_user
):
    product = make_product()
    order = _delivered_order(make_order, product=product)
    review = _review(client, auth, order, product)

    for i in range(2):
        u = make_user("customer", email=f"multi-report-{i}@test.local")
        assert client.post(
            f"/api/reviews/{review['id']}/report",
            json={"reason": f"report {i}"},
            headers=auth(u),
        ).status_code == 201

    assert _reget(Review, review["id"]).status == "flagged"
    assert ReviewReport.query.filter_by(review_id=review["id"]).count() == 2


def test_report_needs_authentication(client, make_order, make_product):
    product = make_product()
    order = _delivered_order(make_order, product=product)
    review = _review_via_service(order, product)

    resp = client.post(
        f"/api/reviews/{review.id}/report", json={"reason": "x"}
    )
    assert resp.status_code in (401, 422)


def _review_via_service(order, product):
    r = review_service.create_review(
        order.user, order.id, {"product_id": product.id}, 3, None, None
    )
    db.session.commit()
    return r


# --------------------------------------------------------------------------- #
# What counts toward the rating at each status
# --------------------------------------------------------------------------- #

def test_flagged_review_still_counts_removed_does_not(
    client, auth, make_order, make_product, make_user
):
    product = make_product()
    a = make_user("customer", email="count-a@test.local")
    b = make_user("customer", email="count-b@test.local")
    order_a = _delivered_order(make_order, product=product, customer=a)
    order_b = _delivered_order(make_order, product=product, customer=b)

    ra = _review(client, auth, order_a, product, rating=2)
    _review(client, auth, order_b, product, rating=4)
    assert _reget(Product, product.id).rating_avg == Decimal("3.00")
    assert _reget(Product, product.id).rating_count == 2

    # Flag ra by reporting it — average unchanged, still 2 counting.
    reporter = make_user("customer", email="count-rep@test.local")
    client.post(
        f"/api/reviews/{ra['id']}/report",
        json={"reason": "unfair"},
        headers=auth(reporter),
    )
    assert _reget(Review, ra["id"]).status == "flagged"
    assert _reget(Product, product.id).rating_avg == Decimal("3.00")
    assert _reget(Product, product.id).rating_count == 2

    # Admin removes ra — now only the rating-4 review counts.
    admin_u = make_user("admin", email="count-admin@test.local")
    resp = client.patch(
        f"/api/admin/reviews/{ra['id']}",
        json={"action": "remove", "reason": "off-topic"},
        headers=auth(admin_u),
    )
    assert resp.status_code == 200
    assert _reget(Product, product.id).rating_avg == Decimal("4.00")
    assert _reget(Product, product.id).rating_count == 1


def test_removed_review_is_absent_from_public_listing_flagged_is_not(
    client, auth, make_order, make_product, make_user
):
    product = make_product()
    reviews = []
    for i in range(3):
        u = make_user("customer", email=f"pub-{i}@test.local")
        order = _delivered_order(make_order, product=product, customer=u)
        reviews.append(_review(client, auth, order, product, rating=i + 3))

    admin_u = make_user("admin", email="pub-admin@test.local")
    reporter = make_user("customer", email="pub-rep@test.local")

    # reviews[0] flagged, reviews[1] removed.
    client.post(
        f"/api/reviews/{reviews[0]['id']}/report",
        json={"reason": "check this"},
        headers=auth(reporter),
    )
    client.patch(
        f"/api/admin/reviews/{reviews[1]['id']}",
        json={"action": "remove", "reason": "abuse"},
        headers=auth(admin_u),
    )

    listed = client.get(
        f"/api/products/{product.id}/reviews"
    ).get_json()
    ids = {r["id"] for r in listed["reviews"]}
    assert reviews[0]["id"] in ids  # flagged still shows
    assert reviews[1]["id"] not in ids  # removed is gone
    assert listed["total"] == 2


# --------------------------------------------------------------------------- #
# Transitions and authorisation
# --------------------------------------------------------------------------- #

def test_restore_brings_a_removed_review_back_and_recounts(
    client, auth, make_order, make_product, make_user
):
    product = make_product()
    order = _delivered_order(make_order, product=product)
    review = _review(client, auth, order, product, rating=5)
    admin_u = make_user("admin", email="restore-admin@test.local")

    client.patch(
        f"/api/admin/reviews/{review['id']}",
        json={"action": "remove", "reason": "mistake"},
        headers=auth(admin_u),
    )
    assert _reget(Product, product.id).rating_count == 0

    resp = client.patch(
        f"/api/admin/reviews/{review['id']}",
        json={"action": "restore", "reason": "false report"},
        headers=auth(admin_u),
    )
    assert resp.status_code == 200
    row = _reget(Review, review["id"])
    assert row.status == "published"
    assert row.moderation_note == "false report"
    assert _reget(Product, product.id).rating_count == 1


def test_moderation_rejects_a_no_op_and_a_bad_action(
    client, auth, make_order, make_product, make_user
):
    product = make_product()
    order = _delivered_order(make_order, product=product)
    review = _review(client, auth, order, product)
    admin_u = make_user("admin", email="noop-admin@test.local")

    bad = client.patch(
        f"/api/admin/reviews/{review['id']}",
        json={"action": "obliterate"},
        headers=auth(admin_u),
    )
    assert bad.status_code == 400
    assert bad.get_json()["code"] == "invalid_action"

    noop = client.patch(
        f"/api/admin/reviews/{review['id']}",
        json={"action": "restore"},  # already published
        headers=auth(admin_u),
    )
    assert noop.status_code == 400
    assert noop.get_json()["code"] == "no_op"


def test_non_admin_cannot_moderate_or_see_the_queue(
    client, auth, make_order, make_product, make_user
):
    product = make_product()
    order = _delivered_order(make_order, product=product)
    review = _review(client, auth, order, product)

    vendor = make_user("vendor", email="mod-vendor@test.local")
    for actor in (order.user, vendor):
        assert client.get(
            "/api/admin/reviews", headers=auth(actor)
        ).status_code == 403
        assert client.patch(
            f"/api/admin/reviews/{review['id']}",
            json={"action": "remove"},
            headers=auth(actor),
        ).status_code == 403

    # And the review was untouched.
    assert _reget(Review, review["id"]).status == "published"


# --------------------------------------------------------------------------- #
# Admin queue contents
# --------------------------------------------------------------------------- #

def test_admin_queue_shows_target_author_and_reporter_reason(
    client, auth, make_order, make_product, make_user
):
    product = make_product(name="Reported Widget")
    order = _delivered_order(make_order, product=product)
    review = _review(client, auth, order, product, rating=1)

    reporter = make_user(
        "customer", email="queue-rep@test.local",
        first_name="Nadia", last_name="Q",
    )
    client.post(
        f"/api/reviews/{review['id']}/report",
        json={"reason": "Fake — never bought it"},
        headers=auth(reporter),
    )

    admin_u = make_user("admin", email="queue-admin@test.local")
    body = client.get(
        "/api/admin/reviews", headers=auth(admin_u)
    ).get_json()

    assert body["total"] == 1
    entry = body["reviews"][0]
    assert entry["status"] == "flagged"
    assert entry["target"] == {
        "type": "product", "id": product.id, "name": "Reported Widget"
    }
    assert entry["author"]["name"] == f"{order.user.first_name} " \
                                      f"{order.user.last_name}"
    assert entry["report_count"] == 1
    assert entry["reports"][0]["reason"] == "Fake — never bought it"
    assert entry["reports"][0]["reporter"]["name"] == "Nadia Q"


def test_reviewable_surfaces_removed_status_and_keeps_the_slot(
    client, auth, make_order, make_product, make_user
):
    product = make_product()
    order = _delivered_order(make_order, product=product)
    rid = _review(client, auth, order, product, rating=2)["id"]

    admin_u = make_user("admin", email="rev-rm-admin@test.local")
    client.patch(
        f"/api/admin/reviews/{rid}",
        json={"action": "remove", "reason": "off-topic rant"},
        headers=auth(admin_u),
    )

    body = client.get(
        f"/api/orders/{order.id}/reviewable", headers=auth(order.user)
    ).get_json()
    entry = body["products"][0]
    assert entry["already_reviewed"] is True
    assert entry["review"]["status"] == "removed"
    # the admin's internal note is never in a customer-facing payload
    assert "moderation_note" not in entry["review"]

    # and the customer cannot slip a fresh review past the removal
    dup = client.post(
        "/api/reviews",
        json={"order_id": order.id, "product_id": product.id, "rating": 5},
        headers=auth(order.user),
    )
    assert dup.status_code == 409
    assert dup.get_json()["code"] == "already_reviewed"


def test_moderation_note_is_not_on_the_public_list(
    client, auth, make_order, make_product, make_user
):
    product = make_product()
    order = _delivered_order(make_order, product=product)
    rid = _review(client, auth, order, product)["id"]

    admin_u = make_user("admin", email="note-leak-admin@test.local")
    # flag with a note, then the review is still publicly visible
    client.patch(
        f"/api/admin/reviews/{rid}",
        json={"action": "flag", "reason": "internal: watching this reviewer"},
        headers=auth(admin_u),
    )
    listed = client.get(
        f"/api/products/{product.id}/reviews"
    ).get_json()["reviews"]
    assert len(listed) == 1
    assert "moderation_note" not in listed[0]


def test_admin_queue_status_filter(
    client, auth, make_order, make_product, make_user
):
    admin_u = make_user("admin", email="filter-admin@test.local")
    published, removed = None, None
    for i in range(2):
        p = make_product()
        o = _delivered_order(make_order, product=p,
                             customer=make_user("customer",
                                                email=f"f-{i}@test.local"))
        r = _review(client, auth, o, p)
        if i == 0:
            published = r
        else:
            removed = r
            client.patch(
                f"/api/admin/reviews/{r['id']}",
                json={"action": "remove", "reason": "x"},
                headers=auth(admin_u),
            )

    def ids(status):
        return {
            e["id"]
            for e in client.get(
                f"/api/admin/reviews?status={status}", headers=auth(admin_u)
            ).get_json()["reviews"]
        }

    assert ids("published") == {published["id"]}
    assert ids("removed") == {removed["id"]}
    assert ids("all") == {published["id"], removed["id"]}
    # default "queue" is empty here — nothing flagged, nothing reported
    assert client.get(
        "/api/admin/reviews", headers=auth(admin_u)
    ).get_json()["total"] == 0
