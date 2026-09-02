"""Reviews, and the product/store rating aggregates — the only writer of both.

A review requires a **verified purchase**: a ``delivered`` order that belongs
to the reviewer and actually contains the thing being reviewed (the product,
by order item; the store, by ``order.store_id``). This is the single most
valuable anti-spam decision in the feature — most junk never gets an order to
attach to.

``rating_avg`` / ``rating_count`` are **recomputed**, never incremented:
one ``SELECT AVG(rating), COUNT(*) ... WHERE <target> AND status='published'``
inside the same transaction as the change. Incrementing a counter here is the
same lost-update bug the stock decrement avoids with a conditional UPDATE
(CL-06). See docs/decisions/0015-review-rating-aggregates.md.

Route handlers parse the request, call one function here, and commit.
Business-rule failures raise ``ReviewError`` carrying the exact status and
JSON body ({"error": msg, "code": ...}) — the OrderError shape.
"""

from datetime import datetime, timezone
from decimal import ROUND_HALF_UP, Decimal

from sqlalchemy import func, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import selectinload

from app.extensions import db
from app.models.order import Order
from app.models.product import Product
from app.models.review import Review
from app.models.review_report import ReviewReport
from app.models.store import Store

PUBLISHED = "published"
FLAGGED = "flagged"
REMOVED = "removed"
REVIEW_STATUSES = (PUBLISHED, FLAGGED, REMOVED)

# published and flagged both count toward a rating and stay publicly
# visible; a report only surfaces a review in the admin queue. Removal is
# the one action that hides it and drops it from the average. ADR 0017.
COUNTING_STATUSES = (PUBLISHED, FLAGGED)

# action -> (resulting status, statuses it may be applied from)
MODERATION_ACTIONS = {
    "flag": (FLAGGED, (PUBLISHED,)),
    "remove": (REMOVED, (PUBLISHED, FLAGGED)),
    "restore": (PUBLISHED, (FLAGGED, REMOVED)),
}

RATING_MIN, RATING_MAX = 1, 5

REASON_MAX = 500

_UNSET = object()


class ReviewError(Exception):
    """A review operation that failed a business rule (OrderError shape)."""

    def __init__(self, message, status_code=400, *, code=None, **extra):
        super().__init__(message)
        self.status_code = status_code
        self.payload = {"error": message}
        if code:
            self.payload["code"] = code
        self.payload.update(extra)


def _now():
    return datetime.now(timezone.utc)


def _validate_rating(rating):
    if not isinstance(rating, int) or isinstance(rating, bool):
        raise ReviewError("Rating must be a whole number 1-5",
                          code="invalid_rating")
    if not RATING_MIN <= rating <= RATING_MAX:
        raise ReviewError("Rating must be between 1 and 5",
                          code="invalid_rating")


def _clean_text(value, limit, field):
    if value is None:
        return None
    if not isinstance(value, str):
        raise ReviewError(f"{field} must be text", code="invalid_field")
    value = value.strip()
    if not value:
        return None
    if len(value) > limit:
        raise ReviewError(f"{field} must be {limit} characters or fewer",
                          code="invalid_field")
    return value


# --------------------------------------------------------------------------- #
# The verified-purchase gate
# --------------------------------------------------------------------------- #

def _resolve_target(target):
    """``target`` is ``{"product_id": n}`` or ``{"store_id": n}`` — exactly one.

    Returns ``("product", Product)`` or ``("store", Store)``.
    """
    product_id = target.get("product_id") if target else None
    store_id = target.get("store_id") if target else None

    if bool(product_id) == bool(store_id):
        raise ReviewError(
            "A review targets exactly one of a product or a store",
            code="invalid_target",
        )

    if product_id:
        product = db.session.get(Product, product_id)
        if product is None:
            raise ReviewError("Product not found", 404, code="product_not_found")
        return "product", product

    store = db.session.get(Store, store_id)
    if store is None:
        raise ReviewError("Store not found", 404, code="store_not_found")
    return "store", store


def _assert_verified_purchase(user, order, kind, entity):
    if order is None:
        raise ReviewError("Order not found", 404, code="order_not_found")
    if order.user_id != user.id:
        raise ReviewError(
            "You can only review your own orders", 403, code="not_your_order"
        )
    if order.status != "delivered":
        raise ReviewError(
            "You can review an order only after it has been delivered",
            400,
            code="order_not_delivered",
        )

    if kind == "product":
        if not any(item.product_id == entity.id for item in order.items):
            raise ReviewError(
                "That product is not in this order",
                400,
                code="product_not_in_order",
            )
    else:  # store
        if order.store_id != entity.id:
            raise ReviewError(
                "That store did not fulfil this order",
                400,
                code="store_not_in_order",
            )


# --------------------------------------------------------------------------- #
# Rating aggregate — recompute, never increment (ADR 0015)
# --------------------------------------------------------------------------- #

def _recalculate_rating(kind, entity):
    """Recompute (avg, count) from the counting rows in one query.

    Counting = every status except 'removed' (ADR 0017). Never
    read-modify-write — that is the CL-06 lost-update hazard (ADR 0015).
    """
    where = (
        Review.product_id == entity.id
        if kind == "product"
        else Review.store_id == entity.id
    )

    avg, count = db.session.execute(
        select(func.avg(Review.rating), func.count(Review.id)).where(
            where, Review.status.in_(COUNTING_STATUSES)
        )
    ).one()

    entity.rating_count = int(count or 0)
    entity.rating_avg = (
        Decimal(str(avg)).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
        if avg is not None
        else None
    )


def _entity_for_review(review):
    if review.product_id is not None:
        return "product", db.session.get(Product, review.product_id)
    return "store", db.session.get(Store, review.store_id)


# --------------------------------------------------------------------------- #
# Writes — caller commits
# --------------------------------------------------------------------------- #

def create_review(user, order_id, target, rating, title, body):
    """Create a verified-purchase review and refresh the target's rating."""
    _validate_rating(rating)
    kind, entity = _resolve_target(target)
    title = _clean_text(title, 120, "Title")
    body = _clean_text(body, 5000, "Review")

    order = db.session.get(Order, order_id)
    _assert_verified_purchase(user, order, kind, entity)

    product_id = entity.id if kind == "product" else None
    store_id = entity.id if kind == "store" else None

    # Friendly pre-check; the two unique constraints are the backstop for a
    # race between two identical submissions (caught just below).
    if Review.query.filter_by(
        user_id=user.id,
        order_id=order_id,
        product_id=product_id,
        store_id=store_id,
    ).first() is not None:
        raise ReviewError(
            f"You have already reviewed this {kind} for this order",
            409,
            code="already_reviewed",
        )

    review = Review(
        user_id=user.id,
        order_id=order_id,
        product_id=product_id,
        store_id=store_id,
        rating=rating,
        title=title,
        body=body,
    )
    db.session.add(review)

    try:
        db.session.flush()
    except IntegrityError:
        db.session.rollback()
        raise ReviewError(
            f"You have already reviewed this {kind} for this order",
            409,
            code="already_reviewed",
        )

    _recalculate_rating(kind, entity)
    return review


def update_review(user, review_id, rating=_UNSET, title=_UNSET, body=_UNSET):
    """Owner-only edit. Touches ``updated_at`` and refreshes the rating."""
    review = db.session.get(Review, review_id)
    if review is None:
        raise ReviewError("Review not found", 404, code="review_not_found")
    if review.user_id != user.id:
        raise ReviewError(
            "You can only edit your own review", 403, code="not_your_review"
        )

    if rating is not _UNSET:
        _validate_rating(rating)
        review.rating = rating
    if title is not _UNSET:
        review.title = _clean_text(title, 120, "Title")
    if body is not _UNSET:
        review.body = _clean_text(body, 5000, "Review")

    review.updated_at = _now()

    kind, entity = _entity_for_review(review)
    _recalculate_rating(kind, entity)
    return review


def delete_review(user, review_id):
    """Owner-only delete. Refreshes the target's rating afterwards."""
    review = db.session.get(Review, review_id)
    if review is None:
        raise ReviewError("Review not found", 404, code="review_not_found")
    if review.user_id != user.id:
        raise ReviewError(
            "You can only delete your own review", 403, code="not_your_review"
        )

    kind, entity = _entity_for_review(review)
    db.session.delete(review)
    db.session.flush()
    _recalculate_rating(kind, entity)


def _transition(review, new_status, note=_UNSET):
    """Move a review to ``new_status`` and refresh its target's rating.

    The single seam every status change goes through, so the recompute can
    never be forgotten. ``note`` (when given) is stored as the moderation
    note; pass it only for admin actions.
    """
    review.status = new_status
    if note is not _UNSET:
        review.moderation_note = note
    review.updated_at = _now()

    kind, entity = _entity_for_review(review)
    _recalculate_rating(kind, entity)


def set_review_status(review_id, new_status):
    """Direct status set for tests / seed. The admin path uses
    :func:`moderate_review`."""
    if new_status not in REVIEW_STATUSES:
        raise ReviewError(
            "status must be one of " + ", ".join(REVIEW_STATUSES),
            code="invalid_status",
        )
    review = db.session.get(Review, review_id)
    if review is None:
        raise ReviewError("Review not found", 404, code="review_not_found")
    _transition(review, new_status)
    return review


def report_review(user, review_id, reason):
    """Record one user's report of a review; flag it if still published.

    Any authenticated user, once per review. The first report on a
    ``published`` review moves it to ``flagged`` so it shows in the admin
    queue — it stays visible and keeps counting until an admin removes it.
    """
    reason = _clean_text(reason, REASON_MAX, "Reason")
    if not reason:
        raise ReviewError(
            "A reason is required to report a review", code="reason_required"
        )

    review = db.session.get(Review, review_id)
    if review is None or review.status == REMOVED:
        raise ReviewError("Review not found", 404, code="review_not_found")

    if ReviewReport.query.filter_by(
        review_id=review_id, user_id=user.id
    ).first() is not None:
        raise ReviewError(
            "You have already reported this review",
            409,
            code="already_reported",
        )

    report = ReviewReport(
        review_id=review_id, user_id=user.id, reason=reason
    )
    db.session.add(report)
    try:
        db.session.flush()
    except IntegrityError:
        db.session.rollback()
        raise ReviewError(
            "You have already reported this review",
            409,
            code="already_reported",
        )

    if review.status == PUBLISHED:
        _transition(review, FLAGGED)

    return report


def moderate_review(review_id, action, reason):
    """Admin action: ``flag`` / ``remove`` / ``restore``. Records the reason
    and refreshes the rating."""
    if action not in MODERATION_ACTIONS:
        raise ReviewError(
            "action must be one of " + ", ".join(MODERATION_ACTIONS),
            code="invalid_action",
        )
    target_status, allowed_from = MODERATION_ACTIONS[action]

    review = db.session.get(Review, review_id)
    if review is None:
        raise ReviewError("Review not found", 404, code="review_not_found")

    if review.status == target_status:
        raise ReviewError(
            f"Review is already {target_status}", code="no_op"
        )
    if review.status not in allowed_from:
        raise ReviewError(
            f"Cannot {action} a review that is {review.status}",
            code="invalid_transition",
        )

    _transition(review, target_status, note=_clean_text(
        reason, REASON_MAX, "Reason"
    ))
    return review


# --------------------------------------------------------------------------- #
# Reads
# --------------------------------------------------------------------------- #

def _serialize(review):
    return review.to_dict()


def list_public_for(kind, entity_id, page, per_page):
    """Public review list for a product or store: everything except
    ``removed`` (flagged reviews stay visible — ADR 0017), newest first."""
    column = Review.product_id if kind == "product" else Review.store_id
    pagination = (
        Review.query.filter(
            column == entity_id, Review.status != REMOVED
        )
        .order_by(Review.created_at.desc(), Review.id.desc())
        .paginate(page=page, per_page=per_page, error_out=False)
    )
    return {
        "reviews": [_serialize(r) for r in pagination.items],
        "page": pagination.page,
        "pages": max(pagination.pages, 1),
        "total": pagination.total,
    }


def _admin_serialize(review):
    if review.product_id is not None:
        target = {
            "type": "product",
            "id": review.product_id,
            "name": review.product.name_en if review.product else None,
        }
    else:
        target = {
            "type": "store",
            "id": review.store_id,
            "name": review.store.name if review.store else None,
        }

    author = review.user
    return {
        **review.to_dict(),
        "moderation_note": review.moderation_note,
        "author": {
            "id": review.user_id,
            "name": (
                f"{author.first_name} {author.last_name}"
                if author
                else None
            ),
            "email": author.email if author else None,
        },
        "target": target,
        "report_count": len(review.reports),
        "reports": [rp.to_dict() for rp in review.reports],
    }


def admin_list_reviews(status_filter, page, per_page):
    """Moderation queue. ``status_filter``: one of the review statuses,
    ``all``, or (default) ``queue`` = everything still needing a decision,
    which is exactly the ``flagged`` set — a report always flags, and
    remove / restore both clear the flag."""
    query = Review.query.options(
        selectinload(Review.reports).selectinload(ReviewReport.user),
        selectinload(Review.user),
        selectinload(Review.product),
        selectinload(Review.store),
    )

    if status_filter in REVIEW_STATUSES:
        query = query.filter(Review.status == status_filter)
    elif status_filter != "all":
        query = query.filter(Review.status == FLAGGED)

    pagination = query.order_by(
        Review.updated_at.desc(), Review.id.desc()
    ).paginate(page=page, per_page=per_page, error_out=False)

    return {
        "reviews": [_admin_serialize(r) for r in pagination.items],
        "page": pagination.page,
        "pages": max(pagination.pages, 1),
        "total": pagination.total,
    }


def reviewable_for_order(user, order_id):
    """What this order still lets the user review, so the UI need not guess."""
    order = db.session.get(Order, order_id)
    if order is None:
        raise ReviewError("Order not found", 404, code="order_not_found")
    if order.user_id != user.id:
        raise ReviewError(
            "You can only review your own orders", 403, code="not_your_order"
        )

    # Every review the user wrote against this order, INCLUDING removed
    # ones. A removed review still holds its (user, order, target) slot —
    # the unique constraint blocks a replacement — so the honest thing is
    # to keep already_reviewed=True and surface status="removed" so the UI
    # can say a moderator took it down, rather than pretend it never
    # existed and offer a "write a review" button that would 409. See
    # docs/decisions/0017-review-moderation.md.
    mine = [r for r in order.reviews if r.user_id == user.id]
    product_review = {
        r.product_id: r for r in mine if r.product_id is not None
    }
    store_review = next((r for r in mine if r.store_id is not None), None)

    can_review = order.status == "delivered"

    def _names(product):
        # Every translation, so the client picks the display language (C.5).
        return {
            "name": product.name_en if product else None,
            "name_en": product.name_en if product else None,
            "name_ar": product.name_ar if product else None,
            "name_fr": product.name_fr if product else None,
        }

    seen = set()
    products = []
    for item in order.items:
        if item.product_id in seen:
            continue
        seen.add(item.product_id)
        existing = product_review.get(item.product_id)
        products.append({
            "id": item.product_id,
            **_names(item.product),
            "already_reviewed": existing is not None,
            "review": existing.to_dict() if existing else None,
        })

    return {
        "order_id": order.id,
        "order_status": order.status,
        "can_review": can_review,
        "store": {
            "id": order.store_id,
            "name": order.store.name if order.store else None,
            "already_reviewed": store_review is not None,
            "review": store_review.to_dict() if store_review else None,
        },
        "products": products,
    }
