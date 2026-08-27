import hashlib

from flask import Blueprint, jsonify, request
from flask_jwt_extended import get_jwt_identity, jwt_required

from app.extensions import db
from app.models import PaymentMethod


payment_method_bp = Blueprint(
    "payment_methods",
    __name__,
    url_prefix="/api/payment-methods"
)


CARD_TYPE = "card"


def hash_card_number(card_number):
    return hashlib.sha256(card_number.encode("utf-8")).hexdigest()


def payment_method_to_dict(payment_method):
    return {
        "id": payment_method.id,
        "type": payment_method.type,
        "label": payment_method.label,
        "brand": payment_method.brand,
        "last4": payment_method.last4,
        "provider": payment_method.provider,
        "provider_customer_id": payment_method.provider_customer_id,
        "provider_payment_method_id": (
            payment_method.provider_payment_method_id
        ),
        "is_default": payment_method.is_default,
        "created_at": (
            payment_method.created_at.isoformat()
            if payment_method.created_at
            else None
        ),
        "updated_at": (
            payment_method.updated_at.isoformat()
            if payment_method.updated_at
            else None
        ),
    }


def get_saved_card(payment_method_id, user_id):
    return PaymentMethod.query.filter_by(
        id=payment_method_id,
        user_id=user_id,
        type=CARD_TYPE
    ).first()


def validate_card_number(card_number):
    if not card_number:
        return None, "Card number is required"

    normalized_number = str(card_number).replace(" ", "").strip()

    if not normalized_number.isdigit():
        return None, "Card number must contain only digits"

    if not 12 <= len(normalized_number) <= 19:
        return None, "Card number must contain between 12 and 19 digits"

    return normalized_number, None


def normalize_optional_value(value):
    return str(value).strip() if value else None


def invalid_saved_method_response():
    return jsonify({
        "message": "Saved payment methods must be cards"
    }), 400


@payment_method_bp.route("", methods=["GET"])
@jwt_required()
def get_payment_methods():
    current_user_id = int(get_jwt_identity())

    payment_methods = PaymentMethod.query.filter_by(
        user_id=current_user_id,
        type=CARD_TYPE
    ).order_by(
        PaymentMethod.is_default.desc(),
        PaymentMethod.created_at.desc()
    ).all()

    return jsonify({
        "payment_methods": [
            payment_method_to_dict(method)
            for method in payment_methods
        ]
    }), 200


@payment_method_bp.route("", methods=["POST"])
@jwt_required()
def create_payment_method():
    current_user_id = int(get_jwt_identity())
    data = request.get_json() or {}

    if data.get("type") != CARD_TYPE:
        return invalid_saved_method_response()

    label = data.get("label")

    if not label or not str(label).strip():
        return jsonify({
            "message": "Cardholder name is required"
        }), 400

    card_number, validation_error = validate_card_number(
        data.get("card_number")
    )

    if validation_error:
        return jsonify({"message": validation_error}), 400

    is_default = bool(data.get("is_default", False))

    if is_default:
        PaymentMethod.query.filter_by(
            user_id=current_user_id,
            type=CARD_TYPE,
            is_default=True
        ).update({"is_default": False})

    existing_cards = PaymentMethod.query.filter_by(
        user_id=current_user_id,
        type=CARD_TYPE
    ).count()

    new_payment_method = PaymentMethod(
        user_id=current_user_id,
        type=CARD_TYPE,
        label=str(label).strip(),
        brand=normalize_optional_value(data.get("brand")),
        last4=card_number[-4:],
        number_hash=hash_card_number(card_number),
        provider=normalize_optional_value(data.get("provider")),
        provider_customer_id=normalize_optional_value(
            data.get("provider_customer_id")
        ),
        provider_payment_method_id=normalize_optional_value(
            data.get("provider_payment_method_id")
        ),
        is_default=is_default or existing_cards == 0
    )

    db.session.add(new_payment_method)
    db.session.commit()

    return jsonify({
        "message": "Card added successfully",
        "payment_method": payment_method_to_dict(new_payment_method)
    }), 201


@payment_method_bp.route("/<int:payment_method_id>", methods=["GET"])
@jwt_required()
def get_payment_method(payment_method_id):
    current_user_id = int(get_jwt_identity())
    payment_method = get_saved_card(payment_method_id, current_user_id)

    if not payment_method:
        return jsonify({"message": "Saved card not found"}), 404

    return jsonify({
        "payment_method": payment_method_to_dict(payment_method)
    }), 200


@payment_method_bp.route("/<int:payment_method_id>", methods=["PUT"])
@jwt_required()
def update_payment_method(payment_method_id):
    current_user_id = int(get_jwt_identity())
    payment_method = get_saved_card(payment_method_id, current_user_id)

    if not payment_method:
        return jsonify({"message": "Saved card not found"}), 404

    data = request.get_json() or {}

    if data.get("type") != CARD_TYPE:
        return invalid_saved_method_response()

    label = data.get("label")

    if not label or not str(label).strip():
        return jsonify({
            "message": "Cardholder name is required"
        }), 400

    card_number = data.get("card_number")

    if card_number:
        card_number, validation_error = validate_card_number(card_number)

        if validation_error:
            return jsonify({"message": validation_error}), 400

        payment_method.last4 = card_number[-4:]
        payment_method.number_hash = hash_card_number(card_number)

    is_default = bool(data.get("is_default", payment_method.is_default))

    if is_default:
        PaymentMethod.query.filter(
            PaymentMethod.user_id == current_user_id,
            PaymentMethod.type == CARD_TYPE,
            PaymentMethod.id != payment_method_id,
            PaymentMethod.is_default.is_(True)
        ).update({"is_default": False})

    payment_method.label = str(label).strip()
    payment_method.brand = normalize_optional_value(data.get("brand"))
    payment_method.provider = normalize_optional_value(data.get("provider"))
    payment_method.provider_customer_id = normalize_optional_value(
        data.get("provider_customer_id")
    )
    payment_method.provider_payment_method_id = normalize_optional_value(
        data.get("provider_payment_method_id")
    )
    payment_method.is_default = is_default

    db.session.commit()

    return jsonify({
        "message": "Card updated successfully",
        "payment_method": payment_method_to_dict(payment_method)
    }), 200


@payment_method_bp.route("/<int:payment_method_id>", methods=["DELETE"])
@jwt_required()
def delete_payment_method(payment_method_id):
    current_user_id = int(get_jwt_identity())
    payment_method = get_saved_card(payment_method_id, current_user_id)

    if not payment_method:
        return jsonify({"message": "Saved card not found"}), 404

    was_default = payment_method.is_default
    db.session.delete(payment_method)
    db.session.flush()

    if was_default:
        replacement = PaymentMethod.query.filter_by(
            user_id=current_user_id,
            type=CARD_TYPE
        ).order_by(PaymentMethod.created_at.desc()).first()

        if replacement:
            replacement.is_default = True

    db.session.commit()

    return jsonify({"message": "Card deleted successfully"}), 200


@payment_method_bp.route(
    "/<int:payment_method_id>/default",
    methods=["PATCH"]
)
@jwt_required()
def set_default_payment_method(payment_method_id):
    current_user_id = int(get_jwt_identity())
    payment_method = get_saved_card(payment_method_id, current_user_id)

    if not payment_method:
        return jsonify({"message": "Saved card not found"}), 404

    PaymentMethod.query.filter_by(
        user_id=current_user_id,
        type=CARD_TYPE,
        is_default=True
    ).update({"is_default": False})

    payment_method.is_default = True
    db.session.commit()

    return jsonify({
        "message": "Default card updated successfully",
        "payment_method": payment_method_to_dict(payment_method)
    }), 200
