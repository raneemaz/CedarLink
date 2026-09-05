from flask import Blueprint, jsonify, request
from flask_jwt_extended import get_jwt_identity

from app.models.store import Store
from app.services import analytics_service, store_service
from app.services.analytics_service import AnalyticsError
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


@vendor_bp.route("/dashboard", methods=["GET"])
@role_required("vendor")
def get_my_dashboard():
    """How the authenticated vendor's own store is doing over a period.

    Scope is not a filter the caller can influence: the store is looked up
    by ``owner_id`` from the token, and the service is handed that store
    rather than an id off the query string. There is no request a vendor
    can make from here that reaches another store's rows.
    """
    user_id = int(get_jwt_identity())

    store = Store.query.filter_by(owner_id=user_id).first()

    if store is None:
        return jsonify({"message": "You do not have a store yet"}), 404

    try:
        dashboard = analytics_service.store_dashboard(
            store,
            request.args.get("from"),
            request.args.get("to"),
        )
    except AnalyticsError as exc:
        return jsonify({"message": str(exc)}), 400

    return jsonify(analytics_service.serialize(dashboard)), 200
