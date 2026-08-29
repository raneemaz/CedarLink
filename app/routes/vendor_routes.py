from flask import Blueprint, jsonify
from flask_jwt_extended import get_jwt_identity

from app.models.store import Store
from app.utils.decorators import role_required

vendor_bp = Blueprint("vendor", __name__, url_prefix="/api/vendor")


@vendor_bp.route("/store", methods=["GET"])
@role_required("vendor")
def get_my_store():
    """Return the authenticated vendor's own store, or 404 if they have none."""
    user_id = int(get_jwt_identity())

    store = Store.query.filter_by(owner_id=user_id).first()

    if store is None:
        return jsonify({"message": "You do not have a store yet"}), 404

    return jsonify({"store": store.to_dict()}), 200
