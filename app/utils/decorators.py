from functools import wraps
from flask_jwt_extended import jwt_required, get_jwt
from flask import jsonify


def role_required(*allowed_roles):
    def decorator(fn):
        @wraps(fn)
        @jwt_required()
        def wrapper(*args, **kwargs):
            claims = get_jwt()
            user_role = claims.get("role")

            if user_role not in allowed_roles:
                return jsonify({
                    "message": "Access denied: insufficient permissions"
                }), 403

            return fn(*args, **kwargs)
        return wrapper
    return decorator


def role_required(*roles):
    def wrapper(fn):
        @wraps(fn)
        @jwt_required()
        def decorated(*args, **kwargs):
            claims = get_jwt()

            if claims.get("role") not in roles:
                return {"message": "Forbidden ❌ role not allowed"}, 403

            return fn(*args, **kwargs)

        return decorated

    return wrapper
