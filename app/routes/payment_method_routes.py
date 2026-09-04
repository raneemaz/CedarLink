from datetime import datetime, timezone

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

# Field names that would carry a full card number or a security code.
# The endpoint refuses a request containing any of them rather than
# ignoring it: silently dropping the field would let an old client keep
# putting a PAN on the wire believing it was being handled, and the wire
# is the part that matters. See docs/decisions/0024-no-card-data.md.
FORBIDDEN_FIELDS = (
    "card_number",
    "cardnumber",
    "card_no",
    "number",
    "full_number",
    "pan",
    "number_hash",
    "cvv",
    "cvc",
    "csc",
    "security_code",
)


def payment_method_to_dict(payment_method):
    return {
        "id": payment_method.id,
        "type": payment_method.type,
        "label": payment_method.label,
        "brand": payment_method.brand,
        "last4": payment_method.last4,
        "exp_month": payment_method.exp_month,
        "exp_year": payment_method.exp_year,
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


def reject_card_data(data):
    """The message for a request carrying a PAN or a CVV, else None.

    This is the whole point of the change: the server cannot leak, log or
    store what it never receives, and an endpoint that never receives a
    card number is out of PCI DSS scope rather than in it and compliant.
    """
    present = [field for field in FORBIDDEN_FIELDS if field in data]

    if not present:
        return None

    return (
        "Card numbers and security codes are not accepted. Send brand, "
        "last four digits, expiry and cardholder name only. Rejected "
        "field(s): " + ", ".join(sorted(present))
    )


def validate_last4(value):
    """The four digits a customer reads off their own card."""
    if value is None or str(value).strip() == "":
        return None, "Last four digits are required"

    digits = str(value).strip()

    if not digits.isdigit() or len(digits) != 4:
        return None, "Last four digits must be exactly four digits"

    return digits, None


def validate_expiry(month, year):
    """(month, year) or an error. Four-digit year, and not in the past."""
    if month is None or year is None or month == "" or year == "":
        return None, None, "Card expiry is required"

    try:
        month = int(month)
        year = int(year)
    except (TypeError, ValueError):
        return None, None, "Card expiry must be numeric"

    if not 1 <= month <= 12:
        return None, None, "Expiry month must be between 1 and 12"

    if not 2000 <= year <= 2099:
        return None, None, "Expiry year must be a four-digit year"

    now = datetime.now(timezone.utc)

    if (year, month) < (now.year, now.month):
        return None, None, "That card has expired"

    return month, year, None


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

    rejection = reject_card_data(data)
    if rejection:
        return jsonify({"message": rejection}), 400

    if data.get("type") != CARD_TYPE:
        return invalid_saved_method_response()

    label = data.get("label")

    if not label or not str(label).strip():
        return jsonify({
            "message": "Cardholder name is required"
        }), 400

    last4, validation_error = validate_last4(data.get("last4"))
    if validation_error:
        return jsonify({"message": validation_error}), 400

    exp_month, exp_year, validation_error = validate_expiry(
        data.get("exp_month"), data.get("exp_year")
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
        last4=last4,
        exp_month=exp_month,
        exp_year=exp_year,
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

    rejection = reject_card_data(data)
    if rejection:
        return jsonify({"message": rejection}), 400

    if data.get("type") != CARD_TYPE:
        return invalid_saved_method_response()

    label = data.get("label")

    if not label or not str(label).strip():
        return jsonify({
            "message": "Cardholder name is required"
        }), 400

    if "last4" in data:
        last4, validation_error = validate_last4(data.get("last4"))
        if validation_error:
            return jsonify({"message": validation_error}), 400
        payment_method.last4 = last4

    if "exp_month" in data or "exp_year" in data:
        exp_month, exp_year, validation_error = validate_expiry(
            data.get("exp_month"), data.get("exp_year")
        )
        if validation_error:
            return jsonify({"message": validation_error}), 400
        payment_method.exp_month = exp_month
        payment_method.exp_year = exp_year

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
