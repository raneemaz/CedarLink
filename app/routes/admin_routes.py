from datetime import datetime, timezone

from flask import Blueprint, request, jsonify
from flask_jwt_extended import jwt_required, get_jwt, get_jwt_identity
from sqlalchemy import func

from app.extensions import db
from app.models.user import User
from app.models.store import Store
from app.models.product import Product
from app.models.order import Order


admin_bp = Blueprint("admin", __name__)


def is_admin():
    return get_jwt().get("role") == "admin"


def _admin_guard():
    if not is_admin():
        return jsonify({"error": "Admin access required"}), 403
    return None


def _user_status(user):
    if user.suspended_at is not None:
        return "suspended"
    if user.deleted_at is not None:
        return "deleted"
    if not user.is_active:
        return "deactivated"
    return "active"


@admin_bp.route("/users", methods=["GET"])
@jwt_required()
def get_all_users():
    guard = _admin_guard()
    if guard:
        return guard

    users = User.query.order_by(User.id.asc()).all()

    return jsonify([
        {
            "id": user.id,
            "first_name": user.first_name,
            "last_name": user.last_name,
            "email": user.email,
            "phone": user.phone,
            "role": user.role,
            "status": _user_status(user),
            "suspension_reason": user.suspension_reason,
        }
        for user in users
    ]), 200


@admin_bp.route("/users/<int:user_id>/suspend", methods=["PATCH"])
@jwt_required()
def suspend_user(user_id):
    guard = _admin_guard()
    if guard:
        return guard

    admin_id = int(get_jwt_identity())

    if user_id == admin_id:
        return jsonify({"error": "You cannot suspend yourself"}), 400

    user = db.session.get(User, user_id)
    if user is None:
        return jsonify({"error": "User not found"}), 404

    if user.role == "admin":
        return jsonify({"error": "Admins cannot be suspended"}), 400

    data = request.get_json() or {}
    reason = (data.get("reason") or "").strip() or None

    user.suspended_at = datetime.now(timezone.utc)
    user.suspension_reason = reason
    db.session.commit()

    return jsonify({
        "message": "User suspended",
        "status": _user_status(user),
        "suspension_reason": user.suspension_reason,
    }), 200


@admin_bp.route("/users/<int:user_id>/unsuspend", methods=["PATCH"])
@jwt_required()
def unsuspend_user(user_id):
    guard = _admin_guard()
    if guard:
        return guard

    user = db.session.get(User, user_id)
    if user is None:
        return jsonify({"error": "User not found"}), 404

    user.suspended_at = None
    user.suspension_reason = None
    db.session.commit()

    return jsonify({
        "message": "User unsuspended",
        "status": _user_status(user),
    }), 200


@admin_bp.route("/stores", methods=["GET"])
@jwt_required()
def get_all_stores():
    guard = _admin_guard()
    if guard:
        return guard

    product_counts = dict(
        db.session.query(Product.store_id, func.count(Product.id))
        .filter(Product.deleted_at.is_(None))
        .group_by(Product.store_id)
        .all()
    )

    stores = Store.query.order_by(Store.id.asc()).all()

    def store_status(store):
        if store.deleted_at is not None:
            return "removed"
        return "active" if store.is_active else "inactive"

    return jsonify([
        {
            "id": store.id,
            "name": store.name,
            "location": store.location,
            "owner_id": store.owner_id,
            "owner_name": (
                f"{store.owner.first_name} {store.owner.last_name}"
                if store.owner
                else None
            ),
            "owner_email": store.owner.email if store.owner else None,
            "status": store_status(store),
            "is_active": store.is_active,
            "deleted_at": (
                store.deleted_at.isoformat() if store.deleted_at else None
            ),
            "product_count": product_counts.get(store.id, 0),
        }
        for store in stores
    ]), 200


@admin_bp.route("/stores/<int:store_id>", methods=["DELETE"])
@jwt_required()
def delete_store(store_id):
    guard = _admin_guard()
    if guard:
        return guard

    store = db.session.get(Store, store_id)
    if not store:
        return jsonify({"error": "Store not found"}), 404

    if store.deleted_at is not None:
        return jsonify({"error": "Store already removed"}), 400

    # Soft delete — order history for this store is preserved (CL-24).
    store.deleted_at = datetime.now(timezone.utc)
    db.session.commit()

    return jsonify({
        "message": "Store removed. Existing orders are preserved."
    }), 200


@admin_bp.route("/reports", methods=["GET"])
@jwt_required()
def get_reports():
    guard = _admin_guard()
    if guard:
        return guard

    users_by_role = dict(
        db.session.query(User.role, func.count(User.id))
        .group_by(User.role)
        .all()
    )

    stores_removed = Store.query.filter(
        Store.deleted_at.isnot(None)
    ).count()
    stores_active = Store.query.filter(
        Store.deleted_at.is_(None), Store.is_active.is_(True)
    ).count()
    stores_inactive = Store.query.filter(
        Store.deleted_at.is_(None), Store.is_active.is_(False)
    ).count()

    products_live = Product.query.filter(
        Product.deleted_at.is_(None)
    ).count()
    products_deleted = Product.query.filter(
        Product.deleted_at.isnot(None)
    ).count()

    orders_by_status = dict(
        db.session.query(Order.status, func.count(Order.id))
        .group_by(Order.status)
        .all()
    )

    total_order_value = float(
        db.session.query(func.coalesce(func.sum(Order.total_price), 0)).scalar()
    )

    top_stores = [
        {"store": name, "order_count": count}
        for name, count in db.session.query(
            Store.name, func.count(Order.id)
        )
        .join(Order, Order.store_id == Store.id)
        .group_by(Store.id)
        .order_by(func.count(Order.id).desc())
        .limit(5)
        .all()
    ]

    return jsonify({
        "users_by_role": users_by_role,
        "stores": {
            "active": stores_active,
            "inactive": stores_inactive,
            "removed": stores_removed,
        },
        "products": {
            "live": products_live,
            "deleted": products_deleted,
        },
        "orders_by_status": orders_by_status,
        "total_order_value": total_order_value,
        "top_stores_by_orders": top_stores,
    }), 200
