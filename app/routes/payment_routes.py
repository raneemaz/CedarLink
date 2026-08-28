import os

from flask import Blueprint, request, jsonify
from flask_jwt_extended import (
    jwt_required,
    get_jwt_identity,
    get_jwt
)

from app.extensions import db
from app.models.payment import Payment
from app.models.order import Order
from app.models.payment_method import PaymentMethod
from app.services.notification_service import (
    notify_payment_completed,
    notify_payment_refunded,
)


payment_bp = Blueprint("payments", __name__)


PAYMENT_STATUS_TRANSITIONS = {
    "pending": {"completed", "failed"},
    "failed": {"pending"},
    "completed": {"refunded"},
    "refunded": set()
}

PAYMENT_PROVIDERS = {
    "card": "cedarlink",
    "cash_on_delivery": "cedarlink"
}


@payment_bp.route("/payments", methods=["POST"])
@jwt_required()
def create_payment():
    current_user_id = int(get_jwt_identity())
    data = request.get_json() or {}

    order_id = data.get("order_id")
    method = data.get("method")
    payment_method_id = data.get("payment_method_id")

    if not order_id or not method:
        return jsonify({
            "message": "order_id and method are required"
        }), 400

    if method not in PAYMENT_PROVIDERS:
        return jsonify({
            "message": (
                "Invalid payment method. "
                "Allowed methods: card, cash_on_delivery"
            )
        }), 400

    provider = PAYMENT_PROVIDERS[method]

    saved_payment_method = None

    if method == "cash_on_delivery" and payment_method_id is not None:
        return jsonify({
            "message": "Cash on Delivery cannot use a saved payment method"
        }), 400

    if method == "card" and payment_method_id is None:
        return jsonify({
            "message": "A saved card is required for card payments"
        }), 400

    if payment_method_id is not None:
        saved_payment_method = PaymentMethod.query.filter_by(
            id=payment_method_id,
            user_id=current_user_id,
            type="card"
        ).first()

        if not saved_payment_method:
            return jsonify({
                "message": "Saved payment method not found"
            }), 404

        if saved_payment_method.type != method:
            return jsonify({
                "message": (
                    "The selected payment method does not match "
                    "the payment method type"
                )
            }), 400

    order = db.session.get(Order, order_id)

    if not order:
        return jsonify({
            "message": "Order not found"
        }), 404

    if order.user_id != current_user_id:
        return jsonify({
            "message": "only the owner of the order can initiate a payment"
        }), 403

    if order.status != "pending":
        return jsonify({
            "message": "Payments can only be initiated for pending orders"
        }), 400

    existing_payment = Payment.query.filter_by(
        order_id=order.id
    ).first()

    if existing_payment:
        return jsonify({
            "message": (
                "A payment already exists for this order. "
                f"Current payment status: {existing_payment.status}"
            )
        }), 409

    payment = Payment(
        order_id=order.id,
        amount=order.total_price,
        method=method,
        provider=provider,
        payment_method_id=(
            saved_payment_method.id
            if saved_payment_method
            else None
        ),
        status="pending"
    )

    db.session.add(payment)
    db.session.commit()

    return jsonify({
        "message": "Payment initiated successfully",
        "payment": payment.to_dict()
    }), 201


@payment_bp.route("/payments/<int:payment_id>", methods=["GET"])
@jwt_required()
def get_payment(payment_id):
    current_user_id = int(get_jwt_identity())
    claims = get_jwt()
    current_user_role = claims.get("role")

    payment = db.session.get(Payment, payment_id)

    if not payment:
        return jsonify({
            "message": "Payment not found"
        }), 404

    order = payment.order

    if current_user_role == "customer":
        if order.user_id != current_user_id:
            return jsonify({
                "message": "You are not authorized to view this payment"
            }), 403

    elif current_user_role == "vendor":
        if order.store.owner_id != current_user_id:
            return jsonify({
                "message": "You are not authorized to view this payment"
            }), 403

    elif current_user_role == "admin":
        pass

    else:
        return jsonify({
            "message": "You are not authorized to view this payment"
        }), 403

    return jsonify({
        "payment": payment.to_dict()
    }), 200


@payment_bp.route(
    "/payments/webhook/<string:provider>",
    methods=["POST"]
)
def payment_webhook(provider):
    data = request.get_json() or {}

    expected_secret = os.getenv("PAYMENT_WEBHOOK_SECRET")
    received_secret = request.headers.get("X-Webhook-Secret")

    if not expected_secret or received_secret != expected_secret:
        return jsonify({
            "message": "Invalid webhook signature"
        }), 401

    if provider not in set(PAYMENT_PROVIDERS.values()):
        return jsonify({"message": "Unknown payment provider"}), 404

    payment_id = data.get("payment_id")
    result = data.get("status")
    transaction_id = data.get("transaction_id")

    if not payment_id or not result:
        return jsonify({
            "message": "payment_id and status are required"
        }), 400

    if result not in {"completed", "failed", "refunded"}:
        return jsonify({
            "message": (
                "Webhook status must be "
                "completed, failed, or refunded"
            )
        }), 400

    if result == "completed" and not transaction_id:
        return jsonify({
            "message": "transaction_id is required for completed payments"
        }), 400

    payment = db.session.get(Payment, payment_id)

    if not payment:
        return jsonify({
            "message": "Payment not found"
        }), 404

    if payment.provider != provider:
        return jsonify({
            "message": "Payment does not belong to this provider"
        }), 404

    # Allow repeated successful webhook delivery
    if (
        payment.status == "completed"
        and result == "completed"
        and payment.transaction_id == transaction_id
    ):
        return jsonify({
            "message": "Webhook already processed",
            "payment": payment.to_dict()
        }), 200

    # Prevent transaction ID reuse across different payments
    if transaction_id:
        duplicate_transaction = Payment.query.filter(
            Payment.transaction_id == transaction_id,
            Payment.id != payment.id
        ).first()

        if duplicate_transaction:
            return jsonify({
                "message": (
                    "transaction_id already belongs "
                    "to another payment"
                )
            }), 409

    allowed_next_statuses = PAYMENT_STATUS_TRANSITIONS.get(
        payment.status,
        set()
    )

    if result not in allowed_next_statuses:
        return jsonify({
            "message": (
                f"Invalid payment status transition: "
                f"{payment.status} -> {result}"
            )
        }), 409

    payment.status = result

    if transaction_id:
        payment.transaction_id = transaction_id

    if result == "completed":
        payment.order.status = "processing"

    elif result == "refunded":
        payment.order.status = "canceled"

    db.session.commit()

    # Only reached on a real status transition (idempotent re-delivery returns
    # earlier). Notifications are best-effort and isolated from the webhook.
    if result == "completed":
        notify_payment_completed(payment.order)
    elif result == "refunded":
        notify_payment_refunded(payment.order)

    return jsonify({
        "message": f"Payment webhook processed for {provider}",
        "payment": payment.to_dict()
    }), 200
