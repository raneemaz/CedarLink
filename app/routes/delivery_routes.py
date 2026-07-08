from datetime import datetime

from flask import Blueprint, request, jsonify
from flask_jwt_extended import jwt_required, get_jwt_identity

from app.extensions import db
from app.models.delivery_assignment import DeliveryAssignment
from app.models.order import Order
from app.models.store import Store


delivery_bp = Blueprint("delivery_bp", __name__)


@delivery_bp.route("/delivery/assignments", methods=["POST"])
@jwt_required()
def create_delivery_assignment():
    user_id = int(get_jwt_identity())

    data = request.get_json() or {}

    order_id = data.get("order_id")
    driver_name = data.get("driver_name")
    driver_phone = data.get("driver_phone")

    if not order_id:
        return jsonify({
            "error": "order_id is required"
        }), 400

    if not driver_name or not str(driver_name).strip():
        return jsonify({
            "error": "driver_name is required"
        }), 400

    if not driver_phone or not str(driver_phone).strip():
        return jsonify({
            "error": "driver_phone is required"
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

    existing_assignment = DeliveryAssignment.query.filter_by(
        order_id=order.id
    ).first()

    if existing_assignment:
        return jsonify({
            "error": "Delivery assignment already exists for this order"
        }), 409

    try:
        assignment = DeliveryAssignment(
            order_id=order.id,
            driver_name=str(driver_name).strip(),
            driver_phone=str(driver_phone).strip(),
            status="assigned"
        )

        db.session.add(assignment)
        db.session.commit()

        return jsonify({
            "message": "Delivery assignment created successfully",
            "delivery_assignment": assignment.to_dict()
        }), 201

    except Exception:
        db.session.rollback()

        return jsonify({
            "error": "Failed to create delivery assignment"
        }), 500


@delivery_bp.route(
    "/delivery/assignments/<int:id>",
    methods=["GET"]
)
@jwt_required()
def get_delivery_assignment(id):
    user_id = int(get_jwt_identity())

    assignment = db.session.get(
        DeliveryAssignment,
        id
    )

    if not assignment:
        return jsonify({
            "error": "Delivery assignment not found"
        }), 404

    order = db.session.get(
        Order,
        assignment.order_id
    )

    if not order:
        return jsonify({
            "error": "Order not found"
        }), 404

    store = db.session.get(
        Store,
        order.store_id
    )

    if not store:
        return jsonify({
            "error": "Store not found"
        }), 404

    # Customer who owns order OR vendor who owns store
    is_customer_owner = order.user_id == user_id
    is_vendor_owner = store.owner_id == user_id

    if not is_customer_owner and not is_vendor_owner:
        return jsonify({
            "error": "You are not authorized to view this delivery"
        }), 403

    return jsonify({
        "delivery_assignment": assignment.to_dict()
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

    assignment = db.session.get(
        DeliveryAssignment,
        id
    )

    if not assignment:
        return jsonify({
            "error": "Delivery assignment not found"
        }), 404

    order = db.session.get(
        Order,
        assignment.order_id
    )

    if not order:
        return jsonify({
            "error": "Order not found"
        }), 404

    store = db.session.get(
        Store,
        order.store_id
    )

    if not store:
        return jsonify({
            "error": "Store not found"
        }), 404

    # For current CedarLink implementation,
    # store owner updates delivery status
    if store.owner_id != user_id:
        return jsonify({
            "error": "You are not authorized to update this delivery"
        }), 403

    allowed_transitions = {
        "assigned": "picked_up",
        "picked_up": "delivered"
    }

    expected_next_status = allowed_transitions.get(
        assignment.status
    )

    if expected_next_status is None:
        return jsonify({
            "error": (
                f"Delivery with status "
                f"'{assignment.status}' cannot be updated"
            )
        }), 400

    if new_status != expected_next_status:
        return jsonify({
            "error": "Invalid delivery status transition",
            "current_status": assignment.status,
            "allowed_next_status": expected_next_status
        }), 400

    try:
        assignment.status = new_status

        if new_status == "delivered":
            assignment.delivered_at = datetime.utcnow()

        db.session.commit()

        return jsonify({
            "message": "Delivery status updated successfully",
            "delivery_assignment": assignment.to_dict()
        }), 200

    except Exception:
        db.session.rollback()

        return jsonify({
            "error": "Failed to update delivery status"
        }), 500
