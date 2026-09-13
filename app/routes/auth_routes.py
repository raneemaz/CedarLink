import logging

from flask import Blueprint, jsonify, request
from flask_limiter.util import get_remote_address
from flask_jwt_extended import (
    create_access_token,
    get_jwt,
    get_jwt_identity,
    jwt_required,
)
from sqlalchemy.exc import SQLAlchemyError
from werkzeug.security import check_password_hash, generate_password_hash

from app.extensions import db, limiter
from app.models import User
from app.services.account_service import reactivate_account
from app.services.token_service import (
    revoke_current_token,
    revoke_refresh_token,
)
from app.services.two_factor_service import (
    TwoFactorError,
    create_login_challenge,
    create_registration_challenge,
    decoy_registration_challenge,
    issue_auth_tokens,
    request_password_reset,
    resend_login_code,
    resend_registration_code,
    reset_password,
    verify_login_challenge,
    verify_registration_challenge,
)

logger = logging.getLogger(__name__)


auth_bp = Blueprint("auth", __name__, url_prefix="/api/auth")

# Public registration may only ever create these roles. "admin" is never
# assignable through a public endpoint — it is created out of band via the
# `flask create-admin` CLI command (see app/cli.py).
PUBLIC_REGISTRATION_ROLES = ("customer", "vendor")

# Minimum password length at registration. Deliberately the same 8 the
# password-reset flow (two_factor_service.PASSWORD_RESET_MIN_LENGTH) and
# `flask create-admin` already require. This is a length floor only — there
# is no complexity or breach-list check (stated limitation, ADR 0033).
MIN_PASSWORD_LENGTH = 8


# Per-IP limits stop a single host hammering an endpoint; per-account limits
# stop a botnet spreading a credential-stuffing run for one victim across
# many IPs. Both apply (CL-10).
LOGIN_IP_LIMIT = "10 per minute"
LOGIN_ACCOUNT_LIMIT = "5 per minute"
REGISTER_IP_LIMIT = "5 per minute"
REGISTER_ACCOUNT_LIMIT = "5 per hour"
RESEND_IP_LIMIT = "5 per minute"
PASSWORD_RESET_IP_LIMIT = "5 per minute"
PASSWORD_RESET_ACCOUNT_LIMIT = "5 per hour"


def _account_key():
    """Rate-limit key = the account named in the request, else the caller IP."""
    data = request.get_json(silent=True) or {}
    email = (data.get("email") or "").strip().lower()
    return email or get_remote_address()


def error_response(error):
    payload = {
        "message": str(error)
    }

    if error.retry_after is not None:
        payload["retry_after"] = error.retry_after

    return jsonify(payload), error.status_code


@auth_bp.route("/register", methods=["POST"])
@limiter.limit(REGISTER_IP_LIMIT)
@limiter.limit(REGISTER_ACCOUNT_LIMIT, key_func=_account_key)
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

    # Registration accepted any non-empty password until the security pass
    # (ADR 0033). The floor matches the reset flow and the admin CLI, which
    # already enforced it — this closes the one path that did not.
    if len(password) < MIN_PASSWORD_LENGTH:
        return jsonify({
            "message": (
                f"Password must be at least {MIN_PASSWORD_LENGTH} characters"
            )
        }), 400

    # Public registration can only create a customer or a vendor. Any other
    # value (notably "admin") is rejected outright — privilege roles are never
    # assignable from an unauthenticated request.
    if role not in PUBLIC_REGISTRATION_ROLES:
        return jsonify({
            "message": "Invalid role. Allowed roles: customer, vendor"
        }), 400

    # Email is the only delivery channel (SMS and WhatsApp were removed
    # in v1 -- see DELIVERY_METHODS in two_factor_service).
    if verification_method not in ["email"]:
        return jsonify({
            "message": "Invalid verification method"
        }), 400

    existing = User.query.filter_by(email=email).first()

    # An abandoned or failed signup must not lock an address forever. A
    # row that was never verified belongs to nobody -- whoever holds that
    # mailbox never proved they wanted the account, and the only way to
    # prove it is another code. So re-registering an unverified address
    # restarts the signup rather than being silently swallowed. Without
    # this, a user who closes the tab before typing the code can never
    # register again: every retry gets the decoy below, no email is sent,
    # and no code they enter can work.
    #
    # A verified, deleted or suspended account still gets the decoy --
    # those are the cases where a real account exists and confirming it
    # would leak something. Both branches return the same status and the
    # same body shape, so a client still cannot tell them apart.
    retry_of_abandoned_signup = (
        existing is not None
        and not existing.is_verified
        and existing.deleted_at is None
        and existing.suspended_at is None
    )

    if existing is not None and not retry_of_abandoned_signup:
        # Do not confirm the address is taken — that is a free account
        # enumeration oracle (CL-10). Answer exactly as we would for a new
        # email, with a decoy challenge that verifies to nothing. Hash the
        # password anyway so the response time matches the real path.
        generate_password_hash(password)

        # Server-side only. The response below is deliberately
        # indistinguishable from a real registration, which is right for
        # security and baffling in development: re-registering a test
        # address returns 201 and a challenge_token, but no user, no
        # challenge and no email exist, so every code entered is refused.
        # The address is not logged -- a log of "who tried to register"
        # would be the same enumeration oracle by another route.
        logger.warning(
            "Registration decoy served for an address that already exists "
            "-- no user created, no challenge, no email sent"
        )

        return jsonify({
            "message": "Registration successful. Verification is required.",
            "registration_verification_required": True,
            **decoy_registration_challenge(email, phone, verification_method),
        }), 201

    if retry_of_abandoned_signup:
        # Overwrite the abandoned attempt with what was just typed --
        # nothing on that row was ever confirmed, so there is nothing to
        # protect. If the send fails, _create_delivery_challenge rolls
        # these edits back along with the challenge.
        existing.first_name = first_name.strip()
        existing.last_name = last_name.strip()
        existing.password = generate_password_hash(password)
        existing.phone = phone.strip()
        existing.role = role
        existing.verification_method = verification_method

        try:
            challenge = create_registration_challenge(
                existing,
                verification_method,
            )

        except TwoFactorError as error:
            db.session.rollback()
            return error_response(error)

        return jsonify({
            "message": "Registration successful. Verification is required.",
            "registration_verification_required": True,
            **challenge
        }), 201

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
        # flush, not commit: the user needs an id for the challenge's
        # user_id, but must not become durable until the code has
        # actually been sent. _create_delivery_challenge commits the two
        # together and rolls both back if the send fails -- committing
        # here defeated that, so a failed send (SMTP down, bad
        # credentials, a rejected recipient) left an unverified user
        # squatting the email address, and the retry then hit the
        # account-enumeration decoy path and appeared to succeed while
        # verifying to nothing.
        db.session.add(new_user)
        db.session.flush()

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
@limiter.limit(RESEND_IP_LIMIT)
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
@limiter.limit(PASSWORD_RESET_IP_LIMIT)
@limiter.limit(PASSWORD_RESET_ACCOUNT_LIMIT, key_func=_account_key)
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
@limiter.limit(LOGIN_IP_LIMIT)
@limiter.limit(LOGIN_ACCOUNT_LIMIT, key_func=_account_key)
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
@limiter.limit(RESEND_IP_LIMIT)
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
@limiter.limit(RESEND_IP_LIMIT)
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


@auth_bp.route("/logout", methods=["POST"])
@jwt_required()
def logout():
    revoke_current_token(get_jwt())

    # The browser also holds a long-lived refresh token; kill it too so the
    # axios interceptor cannot silently mint a fresh session after logout.
    refresh_token = (request.get_json(silent=True) or {}).get("refresh_token")
    if refresh_token:
        revoke_refresh_token(refresh_token)

    return jsonify({"message": "Logged out"}), 200


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
