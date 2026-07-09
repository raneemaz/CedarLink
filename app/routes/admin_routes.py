from flask import Blueprint, jsonify
from flask_jwt_extended import jwt_required, get_jwt

from app.extensions import db
from app.models.user import User
from app.models.store import Store


admin_bp = Blueprint("admin", __name__)


def is_admin():
    claims = get_jwt()
    return claims.get("role") == "admin"


@admin_bp.route("/users", methods=["GET"])
@jwt_required()
def get_all_users():
    if not is_admin():
        return jsonify({
            "error": "Admin access required"
        }), 403

    users = User.query.all()

    return jsonify([
        {
            "id": user.id,
            "first_name": user.first_name,
            "last_name": user.last_name,
            "email": user.email,
            "phone": user.phone,
            "role": user.role
        }
        for user in users
    ]), 200


@admin_bp.route("/stores", methods=["GET"])
@jwt_required()
def get_all_stores():
    if not is_admin():
        return jsonify({
            "error": "Admin access required"
        }), 403

    stores = Store.query.all()

    return jsonify([
        {
            "id": store.id,
            "name": store.name,
            "description": store.description,
            "location": store.location,
            "contact_info": store.contact_info,
            "is_active": store.is_active,
            "owner_id": store.owner_id
        }
        for store in stores
    ]), 200


@admin_bp.route("/stores/<int:store_id>", methods=["DELETE"])
@jwt_required()
def delete_store(store_id):
    if not is_admin():
        return jsonify({
            "error": "Admin access required"
        }), 403

    store = db.session.get(Store, store_id)

    if not store:
        return jsonify({
            "error": "Store not found"
        }), 404

    db.session.delete(store)
    db.session.commit()

    return jsonify({
        "message": "Store deleted successfully"
    }), 200

