import logging

from flask import Blueprint, jsonify, request
from flask_jwt_extended import (
    create_access_token,
    get_jwt_identity,
    jwt_required,
)
from sqlalchemy.exc import SQLAlchemyError
from werkzeug.security import check_password_hash, generate_password_hash

from app.extensions import db
from app.models import User
from app.services.account_service import reactivate_account
from app.services.two_factor_service import (
    TwoFactorError,
    create_login_challenge,
    create_registration_challenge,
    issue_auth_tokens,
    request_password_reset,
    resend_login_code,
    resend_registration_code,
    reset_password,
    verify_login_challenge,
    verify_registration_challenge,
)
from app.utils.decorators import role_required

logger = logging.getLogger(__name__)


auth_bp = Blueprint("auth", __name__, url_prefix="/api/auth")

# Public registration may only ever create these roles. "admin" is never
# assignable through a public endpoint — it is created out of band via the
# `flask create-admin` CLI command (see app/cli.py).
PUBLIC_REGISTRATION_ROLES = ("customer", "vendor")


def error_response(error):
    payload = {
        "message": str(error)
    }

    if error.retry_after is not None:
        payload["retry_after"] = error.retry_after

    return jsonify(payload), error.status_code


@auth_bp.route("/register", methods=["POST"])
def register():
    data = request.get_json() or {}

    first_name = data.get("first_name")
    last_name = data.get("last_name")
    email = data.get("email")
    password = data.get("password")
    phone = data.get("phone")
    # Default to the least-privileged role when the client omits it.
    role = data.get("role") or "customer"
    verification_method = data.get("verification_method")

    if email:
        email = email.strip().lower()

    if not all([
        first_name,
        last_name,
        email,
        password,
        phone,
        verification_method
    ]):
        return jsonify({
            "message": "Missing required fields"
        }), 400

    # Public registration can only create a customer or a vendor. Any other
    # value (notably "admin") is rejected outright — privilege roles are never
    # assignable from an unauthenticated request.
    if role not in PUBLIC_REGISTRATION_ROLES:
        return jsonify({
            "message": "Invalid role. Allowed roles: customer, vendor"
        }), 400

    if verification_method not in [
        "email",
        "sms",
        "whatsapp"
    ]:
        return jsonify({
            "message": "Invalid verification method"
        }), 400

    existing_user = User.query.filter_by(
        email=email
    ).first()

    if existing_user:
        return jsonify({
            "message": "Email already exists"
        }), 400

    new_user = User(
        first_name=first_name.strip(),
        last_name=last_name.strip(),
        email=email,
        password=generate_password_hash(password),
        phone=phone.strip(),
        role=role,
        is_verified=False,
        verification_method=verification_method
    )

    try:
        db.session.add(new_user)
        db.session.commit()

        challenge = create_registration_challenge(
            new_user,
            verification_method
        )

    except TwoFactorError as error:
        db.session.rollback()
        return error_response(error)

    except SQLAlchemyError:
        db.session.rollback()
        logger.exception("Database error while creating user")
        return jsonify({
            "message": "Unable to create account"
        }), 500

    return jsonify({
        "message": "Registration successful. Verification is required.",
        "registration_verification_required": True,
        "user_id": new_user.id,
        **challenge
    }), 201


@auth_bp.route("/register/verify", methods=["POST"])
def verify_registration():
    data = request.get_json() or {}

    try:
        user = verify_registration_challenge(
            data.get("challenge_token"),
            data.get("code")
        )

        user.is_verified = True
        db.session.commit()

    except TwoFactorError as error:
        return error_response(error)

    return jsonify({
        "message": "Account verified successfully",
        **issue_auth_tokens(user)
    }), 200


@auth_bp.route("/register/resend", methods=["POST"])
def resend_registration_verification_code():
    data = request.get_json() or {}

    try:
        payload = resend_registration_code(
            data.get("challenge_token")
        )
    except TwoFactorError as error:
        return error_response(error)

    return jsonify({
        "message": "A new verification code was sent",
        **payload
    }), 200


# The request endpoint returns this same body whether or not the email is
# registered, so it cannot be used to enumerate accounts. (Registration
# still leaks existence via "Email already exists" — noted, not fixed here.)
PASSWORD_RESET_REQUEST_MESSAGE = (
    "If an account exists for that email, a password reset code has "
    "been sent."
)


@auth_bp.route("/password-reset/request", methods=["POST"])
def password_reset_request():
    data = request.get_json() or {}

    email = data.get("email")

    if not email or not str(email).strip():
        return jsonify({
            "message": "Email is required"
        }), 400

    payload = request_password_reset(email)

    return jsonify({
        "message": PASSWORD_RESET_REQUEST_MESSAGE,
        "challenge_token": payload["challenge_token"],
        "method": payload["method"],
    }), 200


@auth_bp.route("/password-reset/confirm", methods=["POST"])
def password_reset_confirm():
    data = request.get_json() or {}

    try:
        reset_password(
            data.get("challenge_token"),
            data.get("code"),
            data.get("new_password"),
        )
    except TwoFactorError as error:
        return error_response(error)

    return jsonify({
        "message": "Your password has been reset. You can sign in now."
    }), 200


@auth_bp.route("/login", methods=["POST"])
def login():
    data = request.get_json() or {}

    email = data.get("email")
    password = data.get("password")

    if not email or not password:
        return jsonify({
            "message": "Missing email or password"
        }), 400

    user = User.query.filter_by(
        email=email.strip().lower()
    ).first()

    if not user:
        return jsonify({
            "message": "Invalid credentials"
        }), 401

    if not check_password_hash(
        user.password,
        password
    ):
        return jsonify({
            "message": "Invalid credentials"
        }), 401

    if not user.is_verified:
        return jsonify({
            "message": "Please verify your account before logging in"
        }), 403

    if user.suspended_at is not None:
        message = "This account has been suspended by an administrator."
        if user.suspension_reason:
            message += f" Reason: {user.suspension_reason}"
        return jsonify({
            "message": message,
            "account_suspended": True
        }), 403

    if user.deleted_at is not None:
        return jsonify({
            "message": "This account has been deleted."
        }), 403

    if not user.is_active:
        return jsonify({
            "message": (
                "Your account is deactivated. Reactivate it to sign in."
            ),
            "account_deactivated": True
        }), 403

    try:
        challenge = create_login_challenge(user)
    except TwoFactorError as error:
        return error_response(error)

    return jsonify({
        "verification_required": True,
        **challenge
    }), 202


@auth_bp.route("/login/verify", methods=["POST"])
def verify_login():
    data = request.get_json() or {}

    try:
        user = verify_login_challenge(
            data.get("challenge_token"),
            data.get("code"),
            data.get("use_recovery_code") is True
        )
    except TwoFactorError as error:
        return error_response(error)

    return jsonify({
        "message": "Login verified successfully",
        **issue_auth_tokens(user)
    }), 200


@auth_bp.route("/login/resend", methods=["POST"])
def resend_login_verification_code():
    data = request.get_json() or {}

    try:
        payload = resend_login_code(
            data.get("challenge_token")
        )
    except TwoFactorError as error:
        return error_response(error)

    return jsonify({
        "message": "A new verification code was sent",
        **payload
    }), 200


@auth_bp.route("/2fa/verify", methods=["POST"])
def verify_two_factor_login():
    data = request.get_json() or {}

    try:
        user = verify_login_challenge(
            data.get("challenge_token"),
            data.get("code"),
            data.get("use_recovery_code") is True
        )
    except TwoFactorError as error:
        return error_response(error)

    return jsonify(
        issue_auth_tokens(user)
    ), 200


@auth_bp.route("/2fa/resend", methods=["POST"])
def resend_two_factor_login_code():
    data = request.get_json() or {}

    try:
        payload = resend_login_code(
            data.get("challenge_token")
        )
    except TwoFactorError as error:
        return error_response(error)

    return jsonify({
        "message": "A new verification code was sent",
        **payload
    }), 200


@auth_bp.route("/refresh", methods=["POST"])
@jwt_required(refresh=True)
def refresh():
    identity = get_jwt_identity()

    user = db.session.get(
        User,
        int(identity)
    )

    if not user:
        return jsonify({
            "message": "User not found"
        }), 404

    if (
        user.deleted_at is not None
        or user.suspended_at is not None
        or not user.is_active
    ):
        return jsonify({
            "message": "This account is no longer active."
        }), 403

    new_access_token = create_access_token(
        identity=str(user.id),
        additional_claims={
            "role": user.role
        }
    )

    return jsonify({
        "access_token": new_access_token
    }), 200


@auth_bp.route("/reactivate", methods=["POST"])
def reactivate():
    data = request.get_json() or {}

    email = data.get("email")
    password = data.get("password")

    if not email or not password:
        return jsonify({
            "message": "Missing email or password"
        }), 400

    user = User.query.filter_by(
        email=email.strip().lower()
    ).first()

    if not user or not check_password_hash(user.password, password):
        return jsonify({
            "message": "Invalid credentials"
        }), 401

    if user.suspended_at is not None:
        return jsonify({
            "message": (
                "This account has been suspended by an administrator and "
                "cannot be reactivated."
            )
        }), 403

    if user.deleted_at is not None:
        return jsonify({
            "message": "This account has been deleted and cannot be restored."
        }), 409

    if user.is_active:
        return jsonify({
            "message": "This account is already active."
        }), 200

    reactivate_account(user)

    return jsonify({
        "message": "Your account has been reactivated. You can sign in now."
    }), 200


@auth_bp.route("/test-admin", methods=["GET"])
@role_required("admin")
def test_admin():
    return jsonify({
        "message": "Welcome Admin!"
    })
