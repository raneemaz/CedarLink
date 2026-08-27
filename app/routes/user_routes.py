from flask import Blueprint, request, jsonify, current_app
from flask_jwt_extended import jwt_required, get_jwt_identity, get_jwt
from werkzeug.security import generate_password_hash, check_password_hash
from app.extensions import db
from app.models import User

user_bp = Blueprint("users", __name__, url_prefix="/api/users")


@user_bp.route("/<int:user_id>", methods=["GET"])
@jwt_required()
def get_user(user_id):
    current_user_id = int(get_jwt_identity())
    claims = get_jwt()
    current_role = claims.get("role")

    # Users can only view their own profile unless they are admin
    if current_user_id != user_id and current_role != "admin":
        return jsonify({"message": "Access denied"}), 403

    user = User.query.get(user_id)

    if not user:
        return jsonify({"message": "User not found"}), 404

    return (
        jsonify(
            {
                "user": {
                    "id": user.id,
                    "first_name": user.first_name,
                    "last_name": user.last_name,
                    "email": user.email,
                    "phone": user.phone,
                    "language": user.language,
                    "currency": user.currency,
                    "role": user.role,
                }
            }
        ),
        200,
    )


@user_bp.route("/<int:user_id>", methods=["PUT"])
@jwt_required()
def update_user(user_id):
    current_user_id = int(get_jwt_identity())

    # Users can only update their own profile
    if current_user_id != user_id:
        return jsonify({"message": "Access denied"}), 403

    user = User.query.get(user_id)

    if not user:
        return jsonify({"message": "User not found"}), 404

    data = request.get_json() or {}

    first_name = data.get("first_name")
    last_name = data.get("last_name")
    email = data.get("email")
    phone = data.get("phone")

    # Validate required profile fields
    if not first_name or not last_name or not email:
        return (
            jsonify(
                {"message": "First name, last name, and email are required"}
            ),
            400,
        )

    # Normalize email exactly like registration
    email = email.strip().lower()

    # Check whether another user already has this email
    existing_user = User.query.filter(
        User.email == email, User.id != user_id
    ).first()

    if existing_user:
        return jsonify({"message": "Email already exists"}), 400

    user.first_name = first_name.strip()
    user.last_name = last_name.strip()
    user.email = email
    user.phone = phone.strip() if phone else None

    db.session.commit()

    return (
        jsonify(
            {
                "message": "Profile updated successfully",
                "user": {
                    "id": user.id,
                    "first_name": user.first_name,
                    "last_name": user.last_name,
                    "email": user.email,
                    "phone": user.phone,
                    "language": user.language,
                    "currency": user.currency,
                    "role": user.role,
                },
            }
        ),
        200,
    )


@user_bp.route("/<int:user_id>/language", methods=["PUT"])
@jwt_required()
def update_language(user_id):
    current_user_id = int(get_jwt_identity())

    if current_user_id != user_id:
        return jsonify({"message": "Access denied"}), 403

    user = User.query.get(user_id)

    if not user:
        return jsonify({"message": "User not found"}), 404

    data = request.get_json() or {}

    language = data.get("language")

    # Validate language
    supported_languages = ["en", "ar", "fr"]

    if language not in supported_languages:
        return (
            jsonify(
                {
                    "message": (
                        "Unsupported language. "
                        "Supported languages are: en, ar, fr"
                    )
                }
            ),
            400,
        )

    user.language = language

    db.session.commit()

    return (
        jsonify(
            {
                "message": "Language preference updated successfully",
                "user": {"id": user.id, "language": user.language},
            }
        ),
        200,
    )


@user_bp.route("/<int:user_id>/currency", methods=["PUT"])
@jwt_required()
def update_currency(user_id):
    current_user_id = int(get_jwt_identity())

    if current_user_id != user_id:
        return jsonify({"message": "Access denied"}), 403

    user = User.query.get(user_id)

    if not user:
        return jsonify({"message": "User not found"}), 404

    data = request.get_json() or {}

    currency = (data.get("currency") or "").upper()

    # Validate currency against the server-controlled list
    supported_currencies = current_app.config["SUPPORTED_CURRENCIES"]

    if currency not in supported_currencies:
        return (
            jsonify(
                {
                    "message": (
                        "Unsupported currency. Supported currencies are: "
                        + ", ".join(supported_currencies)
                    )
                }
            ),
            400,
        )

    user.currency = currency

    db.session.commit()

    return (
        jsonify(
            {
                "message": "Currency preference updated successfully",
                "user": {"id": user.id, "currency": user.currency},
            }
        ),
        200,
    )


@user_bp.route("/<int:user_id>/password", methods=["PUT"])
@jwt_required()
def change_password(user_id):
    current_user_id = int(get_jwt_identity())

    # Users can only change their own password
    if current_user_id != user_id:
        return jsonify({"message": "Access denied"}), 403

    user = User.query.get(user_id)

    if not user:
        return jsonify({"message": "User not found"}), 404

    data = request.get_json() or {}

    current_password = data.get("current_password")
    new_password = data.get("new_password")
    confirm_password = data.get("confirm_password")

    # Check that all password fields were provided
    if not all([current_password, new_password, confirm_password]):
        return (
            jsonify(
                {
                    "message": (
                        "Current password, new password, "
                        "and confirmation password are required"
                    )
                }
            ),
            400,
        )

    # Verify current password
    if not check_password_hash(user.password, current_password):
        return jsonify({"message": "Current password is incorrect"}), 400

    # Confirm new password
    if new_password != confirm_password:
        return jsonify({"message": "New passwords do not match"}), 400

    # Prevent reusing the same password
    if check_password_hash(user.password, new_password):
        return (
            jsonify(
                {
                    "message": "New password must be different "
                    "from the current password"
                }
            ),
            400,
        )

    # Hash and save the new password
    user.password = generate_password_hash(new_password)

    db.session.commit()

    return jsonify({"message": "Password changed successfully"}), 200
