"""Reviews & ratings (C.3) — verified-purchase reviews for products and stores.

Every write goes through ``review_service``; handlers parse, call, commit.
"""

from flask import Blueprint, jsonify, request
from flask_jwt_extended import get_jwt_identity, jwt_required

from app.extensions import db
from app.models.user import User
from app.services import review_service
from app.services.review_service import ReviewError
from app.utils.decorators import role_required
from app.utils.errors import internal_error

review_bp = Blueprint("review_bp", __name__)

_UNSET = review_service._UNSET


def _page_args():
    try:
        page = int(request.args.get("page", 1))
        per_page = int(request.args.get("limit", 10))
    except (TypeError, ValueError):
        return None, None, (
            jsonify({"error": "page and limit must be integers"}), 400
        )
    if page < 1 or per_page < 1:
        return None, None, (
            jsonify({"error": "page and limit must be greater than 0"}), 400
        )
    return page, min(per_page, 50), None


def _current_user():
    return db.session.get(User, int(get_jwt_identity()))


# --------------------------------------------------------------------------- #
# Public reads
# --------------------------------------------------------------------------- #

@review_bp.route("/products/<int:product_id>/reviews", methods=["GET"])
def get_product_reviews(product_id):
    page, per_page, error = _page_args()
    if error:
        return error
    return jsonify(
        review_service.list_public_for("product", product_id, page, per_page)
    ), 200


@review_bp.route("/stores/<int:store_id>/reviews", methods=["GET"])
def get_store_reviews(store_id):
    page, per_page, error = _page_args()
    if error:
        return error
    return jsonify(
        review_service.list_public_for("store", store_id, page, per_page)
    ), 200


@review_bp.route("/orders/<int:order_id>/reviewable", methods=["GET"])
@role_required("customer")
def get_order_reviewable(order_id):
    try:
        result = review_service.reviewable_for_order(
            _current_user(), order_id
        )
    except ReviewError as exc:
        return jsonify(exc.payload), exc.status_code
    return jsonify(result), 200


# --------------------------------------------------------------------------- #
# Writes
# --------------------------------------------------------------------------- #

@review_bp.route("/reviews", methods=["POST"])
@role_required("customer")
def create_review():
    data = request.get_json() or {}

    target = {}
    if data.get("product_id") is not None:
        target["product_id"] = data.get("product_id")
    if data.get("store_id") is not None:
        target["store_id"] = data.get("store_id")

    try:
        review = review_service.create_review(
            _current_user(),
            data.get("order_id"),
            target,
            data.get("rating"),
            data.get("title"),
            data.get("body"),
        )
        db.session.commit()
    except ReviewError as exc:
        db.session.rollback()
        return jsonify(exc.payload), exc.status_code
    except Exception as exc:
        db.session.rollback()
        return internal_error(exc, "review create failed")

    return jsonify({
        "message": "Review submitted",
        "review": review.to_dict(),
    }), 201


@review_bp.route("/reviews/<int:review_id>", methods=["PUT"])
@role_required("customer")
def update_review(review_id):
    data = request.get_json() or {}

    try:
        review = review_service.update_review(
            _current_user(),
            review_id,
            rating=data.get("rating", _UNSET),
            title=data.get("title", _UNSET),
            body=data.get("body", _UNSET),
        )
        db.session.commit()
    except ReviewError as exc:
        db.session.rollback()
        return jsonify(exc.payload), exc.status_code
    except Exception as exc:
        db.session.rollback()
        return internal_error(exc, "review update failed")

    return jsonify({
        "message": "Review updated",
        "review": review.to_dict(),
    }), 200


@review_bp.route("/reviews/<int:review_id>", methods=["DELETE"])
@role_required("customer")
def delete_review(review_id):
    try:
        review_service.delete_review(_current_user(), review_id)
        db.session.commit()
    except ReviewError as exc:
        db.session.rollback()
        return jsonify(exc.payload), exc.status_code
    except Exception as exc:
        db.session.rollback()
        return internal_error(exc, "review delete failed")

    return jsonify({"message": "Review deleted"}), 200


# --------------------------------------------------------------------------- #
# Moderation — report (any authenticated user) and the admin queue
# --------------------------------------------------------------------------- #

@review_bp.route("/reviews/<int:review_id>/report", methods=["POST"])
@jwt_required()
def report_review(review_id):
    data = request.get_json() or {}
    try:
        review_service.report_review(
            _current_user(), review_id, data.get("reason")
        )
        db.session.commit()
    except ReviewError as exc:
        db.session.rollback()
        return jsonify(exc.payload), exc.status_code
    except Exception as exc:
        db.session.rollback()
        return internal_error(exc, "review report failed")

    return jsonify({"message": "Report received"}), 201


@review_bp.route("/admin/reviews", methods=["GET"])
@role_required("admin")
def admin_list_reviews():
    page, per_page, error = _page_args()
    if error:
        return error
    return jsonify(
        review_service.admin_list_reviews(
            request.args.get("status", "queue"), page, per_page
        )
    ), 200


@review_bp.route("/admin/reviews/<int:review_id>", methods=["PATCH"])
@role_required("admin")
def admin_moderate_review(review_id):
    data = request.get_json() or {}
    try:
        review = review_service.moderate_review(
            review_id, data.get("action"), data.get("reason")
        )
        db.session.commit()
    except ReviewError as exc:
        db.session.rollback()
        return jsonify(exc.payload), exc.status_code
    except Exception as exc:
        db.session.rollback()
        return internal_error(exc, "review moderation failed")

    return jsonify({
        "message": f"Review {review.status}",
        "review": review.to_dict(),
    }), 200
