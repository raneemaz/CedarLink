from flask import Blueprint, request, jsonify
from flask_jwt_extended import get_jwt_identity
from sqlalchemy.orm import selectinload
from app.extensions import db
from app.models.store import Store
from app.services import store_service
from app.services.store_service import StoreHoursError
from app.utils.decorators import role_required

store_bp = Blueprint("store", __name__, url_prefix="/api/stores")


def _store_with_status(store):
    """Store payload for the storefront — adds the live open/closed flag."""
    open_now, _ = store_service.is_open_now(store)
    return {**store.to_dict(), "is_open_now": open_now}


def _load_owned_store(store_id):
    """(store, None) when the caller owns it, else (None, (body, code))."""
    store = db.session.get(Store, store_id)
    if not store:
        return None, (jsonify({"message": "Store not found"}), 404)
    if int(store.owner_id) != int(get_jwt_identity()):
        return None, (
            jsonify({"message": "You can only manage your own store"}),
            403,
        )
    return store, None


@store_bp.route("", methods=["POST"])
@role_required("vendor")
def create_store():
    data = request.get_json()

    if not data:
        return jsonify({"message": "Request body is required"}), 400

    required_fields = ["name", "description", "location", "contact_info",
                       "inside_city_delivery_fee", "outside_city_delivery_fee"]

    for field in required_fields:
        value = data.get(field)

        if value is None or str(value).strip() == "":
            return jsonify({"message": f"{field} is required"}), 400

    user_id = int(get_jwt_identity())

    try:
        inside_fee = float(data["inside_city_delivery_fee"])
        outside_fee = float(data["outside_city_delivery_fee"])

        if inside_fee < 0 or outside_fee < 0:
            return jsonify({
                "message": "Delivery fees cannot be negative"
            }), 400

    except (TypeError, ValueError):
        return jsonify({
            "message": "Delivery fees must be numeric"
        }), 400

    store = Store(
        owner_id=user_id,
        name=data["name"],
        description=data["description"],
        location=data["location"],
        contact_info=data["contact_info"],
        inside_city_delivery_fee=inside_fee,
        outside_city_delivery_fee=outside_fee,
    )

    db.session.add(store)
    db.session.commit()

    return jsonify({
        "message": "Store created successfully",
        "store": store.to_dict()
    }), 201


@store_bp.route("", methods=["GET"])
def get_stores():
    """Public store directory — approved, active, non-removed stores only.

    Query params: keyword (name match), location (exact, case-insensitive),
    page, limit, sort=name|newest. Response shape mirrors GET /api/products.
    """
    # selectinload the week's schedule: _store_with_status() calls
    # is_open_now() for every row, which walks store.hours. Without this the
    # directory fires one extra SELECT per store (CL-18).
    query = Store.query.options(selectinload(Store.hours)).filter(
        Store.is_visible
    )

    keyword = request.args.get("keyword", "").strip()
    if keyword:
        query = query.filter(Store.name.ilike(f"%{keyword}%"))

    location = request.args.get("location", "").strip()
    if location:
        query = query.filter(
            db.func.lower(Store.location) == location.lower()
        )

    if request.args.get("sort") == "newest":
        query = query.order_by(Store.id.desc())
    else:
        query = query.order_by(Store.name.asc())

    try:
        page = int(request.args.get("page", 1))
        per_page = int(request.args.get("limit", 10))
    except (TypeError, ValueError):
        return jsonify({
            "message": "page and limit must be integers"
        }), 400

    if page < 1 or per_page < 1:
        return jsonify({
            "message": "page and limit must be greater than 0"
        }), 400

    pagination = query.paginate(
        page=page,
        per_page=per_page,
        error_out=False
    )

    return jsonify({
        "stores": [_store_with_status(store) for store in pagination.items],
        "page": pagination.page,
        "pages": max(pagination.pages, 1),
        "total": pagination.total
    }), 200


@store_bp.route("/<int:store_id>", methods=["GET"])
def get_store(store_id):
    store = db.session.get(Store, store_id)

    # Deactivated or admin-removed stores are absent from the public
    # storefront. The owning vendor manages theirs via /api/vendor/store.
    if not store or not store.is_visible:
        return jsonify({"message": "Store not found"}), 404

    return jsonify({
        "store": _store_with_status(store)
    }), 200


@store_bp.route("/<int:store_id>", methods=["PUT"])
@role_required("vendor")
def update_store(store_id):
    store = db.session.get(Store, store_id)

    if not store:
        return jsonify({"message": "Store not found"}), 404

    current_user = int(get_jwt_identity())

    if int(store.owner_id) != current_user:
        return jsonify({
            "message": "You can only update your own store"
        }), 403

    data = request.get_json()

    if not data:
        return jsonify({"message": "Request body is required"}), 400

    if "name" in data:
        if not str(data["name"]).strip():
            return jsonify({"message": "name cannot be empty"}), 400
        store.name = data["name"]

    if "description" in data:
        if not str(data["description"]).strip():
            return jsonify({"message": "description cannot be empty"}), 400
        store.description = data["description"]

    if "location" in data:
        if not str(data["location"]).strip():
            return jsonify({"message": "location cannot be empty"}), 400
        store.location = data["location"]

    if "contact_info" in data:
        if not str(data["contact_info"]).strip():
            return jsonify({"message": "contact_info cannot be empty"}), 400
        store.contact_info = data["contact_info"]

    if "inside_city_delivery_fee" in data:
        try:
            fee = float(data["inside_city_delivery_fee"])

            if fee < 0:
                return jsonify({
                    "message": "Inside city delivery fee cannot be negative"
                }), 400

            store.inside_city_delivery_fee = fee

        except (TypeError, ValueError):
            return jsonify({
                "message": "Invalid inside city delivery fee"
            }), 400

    if "outside_city_delivery_fee" in data:
        try:
            fee = float(data["outside_city_delivery_fee"])

            if fee < 0:
                return jsonify({
                    "message": "Outside city delivery fee cannot be negative"
                }), 400

            store.outside_city_delivery_fee = fee

        except (TypeError, ValueError):
            return jsonify({
                "message": "Invalid outside city delivery fee"
            }), 400

    if "delivery_available" in data:
        if not isinstance(data["delivery_available"], bool):
            return jsonify({
                "message": "delivery_available must be true or false"
            }), 400

        store.delivery_available = data["delivery_available"]

    db.session.commit()

    return jsonify({
        "message": "Store updated successfully",
        "store": store.to_dict()
    }), 200


@store_bp.route("/<int:store_id>/status", methods=["PATCH"])
@role_required("vendor")
def toggle_store_status(store_id):
    store = db.session.get(Store, store_id)

    if not store:
        return jsonify({
            "message": "Store not found"
        }), 404

    current_user = int(get_jwt_identity())

    if int(store.owner_id) != current_user:
        return jsonify({
            "message": "You can only update your own store"
        }), 403

    data = request.get_json()

    if not data:
        return jsonify({
            "message": "Request body is required"
        }), 400

    if "is_active" not in data:
        return jsonify({
            "message": "is_active is required"
        }), 400

    if not isinstance(data["is_active"], bool):
        return jsonify({
            "message": "is_active must be true or false"
        }), 400

    store.is_active = data["is_active"]

    db.session.commit()

    return jsonify({
        "message": "Store status updated successfully",
        "store": store.to_dict()
    }), 200


# --------------------------------------------------------------------------- #
# Working hours
# --------------------------------------------------------------------------- #

@store_bp.route("/<int:store_id>/hours", methods=["GET"])
def get_store_hours(store_id):
    """Public — the store's weekly schedule (empty list for a closed day)."""
    store = db.session.get(Store, store_id)
    if not store or not store.is_visible:
        return jsonify({"message": "Store not found"}), 404

    return jsonify({
        "hours": [row.to_dict() for row in store.hours]
    }), 200


@store_bp.route("/<int:store_id>/hours", methods=["PUT"])
@role_required("vendor")
def set_store_hours(store_id):
    store, error = _load_owned_store(store_id)
    if error:
        return error

    data = request.get_json() or {}

    try:
        store_service.replace_hours(store, data.get("hours"))
    except StoreHoursError as exc:
        db.session.rollback()
        return jsonify({"message": str(exc)}), 400

    db.session.commit()

    return jsonify({
        "message": "Working hours updated",
        "hours": [row.to_dict() for row in store.hours],
    }), 200


# --------------------------------------------------------------------------- #
# Manual open/closed override
# --------------------------------------------------------------------------- #

@store_bp.route("/<int:store_id>/override", methods=["PATCH"])
@role_required("vendor")
def set_store_override(store_id):
    store, error = _load_owned_store(store_id)
    if error:
        return error

    data = request.get_json() or {}

    try:
        store_service.set_override(
            store,
            data.get("status"),
            data.get("reason"),
            data.get("until"),
        )
    except StoreHoursError as exc:
        return jsonify({"message": str(exc)}), 400

    db.session.commit()

    return jsonify({
        "message": "Override set",
        "store": store.to_dict(),
    }), 200


@store_bp.route("/<int:store_id>/override", methods=["DELETE"])
@role_required("vendor")
def clear_store_override(store_id):
    store, error = _load_owned_store(store_id)
    if error:
        return error

    store_service.clear_override(store)
    db.session.commit()

    return jsonify({
        "message": "Override cleared",
        "store": store.to_dict(),
    }), 200
