from flask import Blueprint, jsonify
from flask_jwt_extended import get_jwt_identity

from app.models.store import Store
from app.services import store_service
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

    # Owner view: includes approval_note (the storefront one does not).
    return jsonify({"store": store_service.owner_store_dict(store)}), 200
