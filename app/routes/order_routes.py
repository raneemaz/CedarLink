from flask import Blueprint, request, jsonify
from flask_jwt_extended import jwt_required, get_jwt_identity

from app.extensions import db
from app.models.payment_method import PaymentMethod
from app.services import order_service
from app.services.coupon_service import CouponError
from app.services.order_service import OrderError
from app.utils.errors import internal_error


order_bp = Blueprint("order_bp", __name__)


def validate_checkout_payment_method(user_id, data):
    method = data.get("payment_method")
    payment_method_id = data.get("payment_method_id")

    # Keep compatibility with the existing checkout payload while the UI
    # moves to an explicit card/COD selection.
    if not method and payment_method_id is not None:
        method = "card"

    if method == "cash_on_delivery":
        if payment_method_id not in (None, ""):
            return "Cash on Delivery cannot use a saved card"
        return None

    if method != "card":
        return "Please select a card or Cash on Delivery"

    if payment_method_id in (None, ""):
        return "Please select a saved card"

    try:
        payment_method_id = int(payment_method_id)
    except (TypeError, ValueError):
        return "Invalid saved card"

    saved_card = PaymentMethod.query.filter_by(
        id=payment_method_id,
        user_id=user_id,
        type="card"
    ).first()

    if not saved_card:
        return "Selected saved card not found"

    return None


@order_bp.route("/orders/preview", methods=["POST"])
@jwt_required()
def checkout_preview():
    user_id = int(get_jwt_identity())
    data = request.get_json() or {}

    try:
        pricing = order_service.price_cart(
            user_id, data.get("delivery_city"), data.get("coupon_code")
        )
    except OrderError as exc:
        return jsonify(exc.payload), exc.status_code
    except CouponError as exc:
        return jsonify(exc.payload), exc.status_code

    return jsonify(order_service.serialize_quote(pricing)), 200


@order_bp.route("/orders", methods=["POST"])
@jwt_required()
def checkout():
    user_id = int(get_jwt_identity())
    data = request.get_json() or {}

    delivery_address = data.get("delivery_address")
    delivery_city = data.get("delivery_city")

    payment_error = validate_checkout_payment_method(user_id, data)
    if payment_error:
        return jsonify({"error": payment_error}), 400

    if not delivery_address or not delivery_address.strip():
        return jsonify({"error": "Delivery address is required"}), 400

    if not delivery_city or not delivery_city.strip():
        return jsonify({"error": "Delivery city is required"}), 400

    try:
        # Only the code is read from the body. Any "discount" the client
        # cares to send is ignored — the amount is computed server-side
        # from the coupon record, in price_cart, and nowhere else.
        result = order_service.checkout(
            user_id,
            delivery_address,
            delivery_city,
            data.get("coupon_code"),
        )
    except OrderError as exc:
        db.session.rollback()
        return jsonify(exc.payload), exc.status_code
    except CouponError as exc:
        db.session.rollback()
        return jsonify(exc.payload), exc.status_code
    except Exception as exc:
        db.session.rollback()
        return internal_error(exc, "checkout failed")

    return jsonify(result), 201


@order_bp.route("/orders", methods=["GET"])
@jwt_required()
def get_orders():
    user_id = int(get_jwt_identity())
    return jsonify({
        "orders": order_service.list_customer_orders(user_id)
    }), 200


@order_bp.route("/orders/<int:id>", methods=["GET"])
@jwt_required()
def get_order(id):
    user_id = int(get_jwt_identity())

    try:
        order = order_service.get_customer_order(user_id, id)
    except OrderError as exc:
        return jsonify(exc.payload), exc.status_code

    return jsonify({"order": order}), 200


@order_bp.route("/vendor/orders", methods=["GET"])
@jwt_required()
def get_vendor_orders():
    user_id = int(get_jwt_identity())

    try:
        orders = order_service.list_vendor_orders(
            user_id, request.args.get("status")
        )
    except OrderError as exc:
        return jsonify(exc.payload), exc.status_code

    return jsonify({"orders": orders}), 200


@order_bp.route("/orders/<int:id>/status", methods=["PATCH"])
@jwt_required()
def update_order_status(id):
    user_id = int(get_jwt_identity())
    data = request.get_json() or {}

    try:
        result = order_service.transition_order_status(
            user_id, id, data.get("status")
        )
    except OrderError as exc:
        return jsonify(exc.payload), exc.status_code
    except Exception as exc:
        db.session.rollback()
        return internal_error(exc, "order status update failed")

    return jsonify(result), 200


@order_bp.route("/orders/<int:id>/cancel", methods=["PATCH"])
@jwt_required()
def cancel_order(id):
    user_id = int(get_jwt_identity())

    try:
        result = order_service.cancel_order(user_id, id)
    except OrderError as exc:
        return jsonify(exc.payload), exc.status_code
    except Exception as exc:
        db.session.rollback()
        return internal_error(exc, "order cancel failed")

    return jsonify(result), 200
