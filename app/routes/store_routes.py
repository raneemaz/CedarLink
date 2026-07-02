from flask import Blueprint
from flask import request, jsonify
from app.extensions import db
from app.models.store import Store
from flask_jwt_extended import jwt_required, get_jwt_identity
from app.utils.decorators import role_required

store_bp = Blueprint("store", __name__, url_prefix="/api/stores")


@store_bp.route("", methods=["POST"])
@role_required("vendor")
def create_store():
    data = request.get_json()

    user_id = get_jwt_identity()

    # create store
    store = Store(
        owner_id=user_id,
        name=data.get("name"),
        description=data.get("description"),
        location=data.get("location"),
        contact_info=data.get("contact_info"),
    )

    db.session.add(store)
    db.session.commit()

    return jsonify({
        "message": "Store created successfully",
        "store": store.to_dict()
    }), 201



@store_bp.route("", methods=["GET"])
@role_required("vendor")
def get_stores():
    stores = Store.query.all()

    return jsonify({
        "stores": [store.to_dict() for store in stores]
    }), 200


@store_bp.route("/<int:store_id>", methods=["GET"])
def get_store(store_id):
    store = Store.query.get(store_id)

    if not store:
        return jsonify({"message": "Store not found ❌"}), 404

    return jsonify({
        "store": store.to_dict()
    }), 200
