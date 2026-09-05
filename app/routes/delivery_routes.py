from flask import Blueprint, request, jsonify
from flask_jwt_extended import jwt_required, get_jwt_identity

from app.extensions import db
from app.models.delivery_assignment import DeliveryAssignment
from app.models.order import Order
from app.models.store import Store
from app.services import delivery_service
from app.services.delivery_service import DeliveryError


delivery_bp = Blueprint("delivery_bp", __name__)


def _load_assignment_context(assignment_id):
    """Assignment, its order and its store — or the 404 to return."""
    assignment = db.session.get(DeliveryAssignment, assignment_id)

    if not assignment:
        raise DeliveryError("Delivery assignment not found", status_code=404)

    order = db.session.get(Order, assignment.order_id)

    if not order:
        raise DeliveryError("Order not found", status_code=404)

    store = db.session.get(Store, order.store_id)

    if not store:
        raise DeliveryError("Store not found", status_code=404)

    return assignment, order, store


@delivery_bp.route("/delivery/assignments", methods=["POST"])
@jwt_required()
def create_delivery_assignment():
    user_id = int(get_jwt_identity())

    data = request.get_json() or {}
    order_id = data.get("order_id")

    if not order_id:
        return jsonify({
            "error": "order_id is required"
        }), 400

    order = db.session.get(Order, order_id)

    if not order:
        return jsonify({
            "error": "Order not found"
        }), 404

    store = db.session.get(Store, order.store_id)

    if not store:
        return jsonify({
            "error": "Store not found"
        }), 404

    # Only the vendor who owns this store can assign delivery
    if store.owner_id != user_id:
        return jsonify({
            "error": "You are not authorized to assign delivery"
        }), 403

    try:
        assignment = delivery_service.assign_driver(
            order,
            data.get("driver_name"),
            data.get("driver_phone"),
        )
    except DeliveryError as exc:
        return jsonify(exc.payload), exc.status_code
    except Exception:
        db.session.rollback()

        return jsonify({
            "error": "Failed to create delivery assignment"
        }), 500

    return jsonify({
        "message": "Delivery assignment created successfully",
        "delivery_assignment": assignment.to_dict(
            include_driver_phone=True
        )
    }), 201


@delivery_bp.route(
    "/delivery/assignments/<int:id>",
    methods=["GET"]
)
@jwt_required()
def get_delivery_assignment(id):
    user_id = int(get_jwt_identity())

    try:
        assignment, order, store = _load_assignment_context(id)
    except DeliveryError as exc:
        return jsonify(exc.payload), exc.status_code

    # Customer who owns order OR vendor who owns store
    is_customer_owner = order.user_id == user_id
    is_vendor_owner = store.owner_id == user_id

    if not is_customer_owner and not is_vendor_owner:
        return jsonify({
            "error": "You are not authorized to view this delivery"
        }), 403

    show_phone = delivery_service.may_disclose_phone(
        assignment, is_vendor=is_vendor_owner
    )

    return jsonify({
        "delivery_assignment": assignment.to_dict(
            include_driver_phone=show_phone
        )
    }), 200


@delivery_bp.route(
    "/delivery/assignments/<int:id>/status",
    methods=["PATCH"]
)
@jwt_required()
def update_delivery_status(id):
    user_id = int(get_jwt_identity())

    data = request.get_json() or {}
    new_status = data.get("status")

    if not new_status:
        return jsonify({
            "error": "Status is required"
        }), 400

    try:
        assignment, order, store = _load_assignment_context(id)
    except DeliveryError as exc:
        return jsonify(exc.payload), exc.status_code

    # For current CedarLink implementation,
    # store owner updates delivery status
    if store.owner_id != user_id:
        return jsonify({
            "error": "You are not authorized to update this delivery"
        }), 403

    try:
        delivery_service.advance_status(assignment, order, new_status)
    except DeliveryError as exc:
        return jsonify(exc.payload), exc.status_code
    except Exception:
        db.session.rollback()

        return jsonify({
            "error": "Failed to update delivery status"
        }), 500

    return jsonify({
        "message": "Delivery status updated successfully",
        "delivery_assignment": assignment.to_dict(
            include_driver_phone=True
        )
    }), 200
