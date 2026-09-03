"""Coupon administration — vendor (store-scoped) and admin (platform-wide).

Two blueprints over one set of helpers, because the two audiences differ in
exactly one way that matters: **a vendor may never create a platform-wide
coupon.** ``store_id`` is not read from the vendor body at all — it is taken
from the URL — so there is no payload that can widen a vendor's coupon
beyond their own store. The admin routes are the only path to a
platform-wide code.

Handlers parse, call, and return; the rules live in ``coupon_service`` and
in the model's CHECK constraints.
"""

from datetime import datetime, timezone
from decimal import Decimal, InvalidOperation

from flask import Blueprint, jsonify, request
from flask_jwt_extended import get_jwt_identity

from app.extensions import db
from app.models.coupon import DISCOUNT_TYPES, Coupon
from app.models.store import Store
from app.services import coupon_service
from app.utils.decorators import role_required

vendor_coupon_bp = Blueprint("vendor_coupons", __name__)
admin_coupon_bp = Blueprint("admin_coupons", __name__)


class _BadRequest(Exception):
    def __init__(self, message):
        super().__init__(message)
        self.message = message


def _load_owned_store(store_id):
    """(store, None) when the caller owns it, else (None, (body, code))."""
    store = db.session.get(Store, store_id)
    if not store:
        return None, (jsonify({"message": "Store not found"}), 404)
    if int(store.owner_id) != int(get_jwt_identity()):
        return None, (
            jsonify({"message": "You can only manage your own store"}),
            403,
        )
    return store, None


def _parse_datetime(value, field):
    if value in (None, ""):
        return None
    try:
        parsed = datetime.fromisoformat(str(value).replace("Z", "+00:00"))
    except ValueError:
        raise _BadRequest(f"{field} must be an ISO 8601 datetime")
    # Stored naive-UTC, matching every other datetime column here.
    if parsed.tzinfo is not None:
        parsed = parsed.astimezone(timezone.utc).replace(tzinfo=None)
    return parsed


def _parse_decimal(value, field, minimum=None):
    try:
        parsed = Decimal(str(value))
    except (InvalidOperation, TypeError, ValueError):
        raise _BadRequest(f"{field} must be a number")
    if minimum is not None and parsed < minimum:
        raise _BadRequest(f"{field} must be at least {minimum}")
    return parsed


def _parse_limit(value, field):
    if value in (None, ""):
        return None
    try:
        parsed = int(value)
    except (TypeError, ValueError):
        raise _BadRequest(f"{field} must be a whole number")
    if parsed < 1:
        raise _BadRequest(f"{field} must be at least 1")
    return parsed


def _validate_value(discount_type, value):
    """The Python-side half of ck_coupons_value_range.

    The CHECK is the real guarantee; this exists so a bad request gets a
    400 naming the field instead of a 500 from an IntegrityError.
    """
    if discount_type == "percentage" and not (1 <= value <= 100):
        raise _BadRequest("A percentage discount must be between 1 and 100")
    if discount_type == "fixed" and value <= 0:
        raise _BadRequest("A fixed discount must be greater than zero")


def _apply_fields(coupon, data, creating):
    """Write the editable fields from ``data`` onto ``coupon``.

    ``store_id`` is deliberately absent: scope is decided by the caller's
    route, never by the body.
    """
    if creating or "code" in data:
        code = coupon_service.normalize_code(data.get("code"))
        if not code:
            raise _BadRequest("code is required")
        if len(code) > 40:
            raise _BadRequest("code must be 40 characters or fewer")
        clash = Coupon.query.filter_by(code=code).first()
        if clash is not None and clash.id != coupon.id:
            raise _BadRequest("That coupon code already exists")
        coupon.code = code

    if creating or "discount_type" in data:
        discount_type = str(data.get("discount_type") or "").strip().lower()
        if discount_type not in DISCOUNT_TYPES:
            raise _BadRequest(
                "discount_type must be 'percentage' or 'fixed'"
            )
        coupon.discount_type = discount_type

    if creating or "value" in data:
        coupon.value = _parse_decimal(data.get("value"), "value")

    _validate_value(coupon.discount_type, Decimal(coupon.value))

    if creating or "min_order_total" in data:
        raw = data.get("min_order_total")
        coupon.min_order_total = (
            None if raw in (None, "")
            else _parse_decimal(raw, "min_order_total", Decimal("0"))
        )

    if creating or "starts_at" in data:
        coupon.starts_at = _parse_datetime(data.get("starts_at"), "starts_at")

    if creating or "ends_at" in data:
        coupon.ends_at = _parse_datetime(data.get("ends_at"), "ends_at")

    if (
        coupon.starts_at is not None
        and coupon.ends_at is not None
        and coupon.ends_at <= coupon.starts_at
    ):
        raise _BadRequest("ends_at must be after starts_at")

    if creating or "usage_limit" in data:
        coupon.usage_limit = _parse_limit(
            data.get("usage_limit"), "usage_limit"
        )

    if creating or "per_user_limit" in data:
        coupon.per_user_limit = _parse_limit(
            data.get("per_user_limit"), "per_user_limit"
        )

    if creating or "is_active" in data:
        coupon.is_active = bool(data.get("is_active", True))


def _create(store_id):
    data = request.get_json() or {}

    coupon = Coupon(store_id=store_id, used_count=0)

    try:
        _apply_fields(coupon, data, creating=True)
    except _BadRequest as exc:
        return jsonify({"message": exc.message}), 400

    db.session.add(coupon)
    db.session.commit()

    return jsonify({
        "message": "Coupon created",
        "coupon": coupon.to_dict(),
    }), 201


def _update(coupon):
    data = request.get_json() or {}

    try:
        _apply_fields(coupon, data, creating=False)
    except _BadRequest as exc:
        db.session.rollback()
        return jsonify({"message": exc.message}), 400

    db.session.commit()

    return jsonify({
        "message": "Coupon updated",
        "coupon": coupon.to_dict(),
    }), 200


def _delete(coupon):
    """Deactivate rather than destroy once a coupon has been redeemed.

    A redemption row is order history and must survive; deleting the coupon
    it points at would break the audit trail (and the FK). An unused coupon
    has no history to protect, so it goes.
    """
    if coupon.redemptions:
        coupon.is_active = False
        db.session.commit()
        return jsonify({
            "message": "Coupon has been redeemed; deactivated instead",
            "coupon": coupon.to_dict(),
        }), 200

    db.session.delete(coupon)
    db.session.commit()

    return jsonify({"message": "Coupon deleted"}), 200


# --------------------------------------------------------------------------- #
# Vendor — store-scoped only
# --------------------------------------------------------------------------- #

def _load_store_coupon(store_id, coupon_id):
    """A coupon that belongs to this store, or an error response.

    The ``store_id`` filter is what stops a vendor editing another store's
    coupon by guessing an id — and a platform-wide coupon (store_id NULL)
    can never match either.
    """
    coupon = Coupon.query.filter_by(id=coupon_id, store_id=store_id).first()
    if not coupon:
        return None, (jsonify({"message": "Coupon not found"}), 404)
    return coupon, None


@vendor_coupon_bp.route("/api/stores/<int:store_id>/coupons",
                        methods=["GET"])
@role_required("vendor", "admin")
def list_store_coupons(store_id):
    store, error = _load_owned_store(store_id)
    if error:
        return error

    coupons = (
        Coupon.query.filter_by(store_id=store.id)
        .order_by(Coupon.created_at.desc())
        .all()
    )

    return jsonify({
        "coupons": [coupon.to_dict() for coupon in coupons]
    }), 200


@vendor_coupon_bp.route("/api/stores/<int:store_id>/coupons",
                        methods=["POST"])
@role_required("vendor", "admin")
def create_store_coupon(store_id):
    store, error = _load_owned_store(store_id)
    if error:
        return error

    # Scope comes from the URL. A "store_id": null in the body changes
    # nothing — a vendor has no route to a platform-wide coupon.
    return _create(store.id)


@vendor_coupon_bp.route("/api/stores/<int:store_id>/coupons/<int:coupon_id>",
                        methods=["PUT"])
@role_required("vendor", "admin")
def update_store_coupon(store_id, coupon_id):
    store, error = _load_owned_store(store_id)
    if error:
        return error

    coupon, error = _load_store_coupon(store.id, coupon_id)
    if error:
        return error

    return _update(coupon)


@vendor_coupon_bp.route("/api/stores/<int:store_id>/coupons/<int:coupon_id>",
                        methods=["DELETE"])
@role_required("vendor", "admin")
def delete_store_coupon(store_id, coupon_id):
    store, error = _load_owned_store(store_id)
    if error:
        return error

    coupon, error = _load_store_coupon(store.id, coupon_id)
    if error:
        return error

    return _delete(coupon)


# --------------------------------------------------------------------------- #
# Admin — platform-wide
# --------------------------------------------------------------------------- #

@admin_coupon_bp.route("/coupons", methods=["GET"])
@role_required("admin")
def admin_list_coupons():
    """Every coupon, platform-wide and store-scoped alike."""
    coupons = Coupon.query.order_by(Coupon.created_at.desc()).all()

    return jsonify({
        "coupons": [coupon.to_dict() for coupon in coupons]
    }), 200


@admin_coupon_bp.route("/coupons", methods=["POST"])
@role_required("admin")
def admin_create_coupon():
    """Platform-wide by default; an explicit store_id scopes it."""
    data = request.get_json() or {}

    store_id = data.get("store_id")

    if store_id is not None:
        if db.session.get(Store, store_id) is None:
            return jsonify({"message": "Store not found"}), 404

    return _create(store_id)


@admin_coupon_bp.route("/coupons/<int:coupon_id>", methods=["PUT"])
@role_required("admin")
def admin_update_coupon(coupon_id):
    coupon = db.session.get(Coupon, coupon_id)

    if not coupon:
        return jsonify({"message": "Coupon not found"}), 404

    return _update(coupon)


@admin_coupon_bp.route("/coupons/<int:coupon_id>", methods=["DELETE"])
@role_required("admin")
def admin_delete_coupon(coupon_id):
    coupon = db.session.get(Coupon, coupon_id)

    if not coupon:
        return jsonify({"message": "Coupon not found"}), 404

    return _delete(coupon)
