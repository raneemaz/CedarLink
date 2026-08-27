from flask import Blueprint, jsonify, request
from flask_jwt_extended import get_jwt_identity, jwt_required
from werkzeug.security import check_password_hash

from app.extensions import db
from app.models import User
from app.services.two_factor_service import (
    SUPPORTED_METHODS,
    TwoFactorError,
    confirm_setup,
    create_security_challenge,
    disable_two_factor,
    generate_recovery_codes,
    start_setup,
    verify_security_challenge,
)

two_factor_bp = Blueprint(
    "two_factor",
    __name__,
    url_prefix="/api/users"
)


def two_factor_error_response(error):
    payload = {"message": str(error)}

    if error.retry_after is not None:
        payload["retry_after"] = error.retry_after

    return jsonify(payload), error.status_code


def get_current_user(user_id):
    current_user_id = int(get_jwt_identity())

    if current_user_id != user_id:
        return None

    return db.session.get(User, user_id)


def security_proof_from_request(user, data):
    verify_security_challenge(
        user,
        data.get("challenge_token"),
        data.get("code"),
        data.get("use_recovery_code") is True
    )


@two_factor_bp.route("/<int:user_id>/2fa", methods=["GET"])
@jwt_required()
def get_two_factor_status(user_id):
    user = get_current_user(user_id)

    if not user:
        return jsonify({"message": "Access denied"}), 403

    return jsonify({
        "two_factor_enabled": user.two_factor_enabled,
        "two_factor_method": (
            user.two_factor_method
            if user.two_factor_enabled
            else None
        )
    }), 200


@two_factor_bp.route("/<int:user_id>/2fa/setup", methods=["POST"])
@jwt_required()
def setup_two_factor(user_id):
    user = get_current_user(user_id)

    if not user:
        return jsonify({"message": "Access denied"}), 403

    if user.two_factor_enabled:
        return jsonify({
            "message": "Use change-method to replace an active 2FA method"
        }), 409

    data = request.get_json(silent=True) or {}

    try:
        payload = start_setup(
            user,
            data.get("method")
        )

    except TwoFactorError as error:
        return two_factor_error_response(error)

    return jsonify({
        "message": "Two-factor setup started",
        **payload
    }), 201


@two_factor_bp.route("/<int:user_id>/2fa/confirm", methods=["POST"])
@jwt_required()
def confirm_two_factor_setup(user_id):
    user = get_current_user(user_id)

    if not user:
        return jsonify({"message": "Access denied"}), 403

    data = request.get_json(silent=True) or {}

    try:
        recovery_codes = confirm_setup(
            user,
            data.get("challenge_token"),
            data.get("code")
        )

    except TwoFactorError as error:
        return two_factor_error_response(error)

    return jsonify({
        "message": "Two-factor authentication enabled",
        "two_factor_enabled": True,
        "two_factor_method": user.two_factor_method,
        "recovery_codes": recovery_codes
    }), 200


@two_factor_bp.route(
    "/<int:user_id>/2fa/security-challenge",
    methods=["POST"]
)
@jwt_required()
def create_two_factor_security_challenge(user_id):
    user = get_current_user(user_id)

    if not user:
        return jsonify({"message": "Access denied"}), 403

    data = request.get_json(silent=True) or {}
    current_password = data.get("current_password")

    if not current_password or not check_password_hash(
        user.password,
        current_password
    ):
        return jsonify({
            "message": "Current password is incorrect"
        }), 401

    try:
        payload = create_security_challenge(user)

    except TwoFactorError as error:
        return two_factor_error_response(error)

    return jsonify({
        "message": "Security verification started",
        **payload
    }), 201


@two_factor_bp.route(
    "/<int:user_id>/2fa/disable",
    methods=["POST"]
)
@jwt_required()
def disable_user_two_factor(user_id):
    user = get_current_user(user_id)

    if not user:
        return jsonify({"message": "Access denied"}), 403

    if not user.two_factor_enabled:
        return jsonify({
            "message": "Two-factor authentication is not enabled"
        }), 409

    data = request.get_json(silent=True) or {}

    try:
        security_proof_from_request(user, data)
        disable_two_factor(user)

    except TwoFactorError as error:
        return two_factor_error_response(error)

    return jsonify({
        "message": "Two-factor authentication disabled",
        "two_factor_enabled": False,
        "two_factor_method": None
    }), 200


@two_factor_bp.route(
    "/<int:user_id>/2fa/change-method",
    methods=["POST"]
)
@jwt_required()
def change_two_factor_method(user_id):
    user = get_current_user(user_id)

    if not user:
        return jsonify({"message": "Access denied"}), 403

    if not user.two_factor_enabled:
        return jsonify({
            "message": "Two-factor authentication is not enabled"
        }), 409

    data = request.get_json(silent=True) or {}
    new_method = data.get("method")

    if new_method not in SUPPORTED_METHODS:
        return jsonify({
            "message": "Unsupported two-factor method"
        }), 400

    if new_method == user.two_factor_method:
        return jsonify({
            "message": "Choose a different two-factor method"
        }), 400

    try:
        # The current method remains active until
        # the new method is successfully confirmed.
        security_proof_from_request(user, data)

        payload = start_setup(
            user,
            new_method
        )

    except TwoFactorError as error:
        return two_factor_error_response(error)

    return jsonify({
        "message": "Verify the new two-factor method to finish the change",
        **payload
    }), 201


@two_factor_bp.route(
    "/<int:user_id>/2fa/recovery-codes/regenerate",
    methods=["POST"]
)
@jwt_required()
def regenerate_two_factor_recovery_codes(user_id):
    user = get_current_user(user_id)

    if not user:
        return jsonify({"message": "Access denied"}), 403

    if not user.two_factor_enabled:
        return jsonify({
            "message": "Two-factor authentication is not enabled"
        }), 409

    data = request.get_json(silent=True) or {}

    try:
        security_proof_from_request(user, data)

        recovery_codes = generate_recovery_codes(user)

        db.session.commit()

    except TwoFactorError as error:
        return two_factor_error_response(error)

    return jsonify({
        "message": "Recovery codes regenerated",
        "recovery_codes": recovery_codes
    }), 200
