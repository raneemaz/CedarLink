from decimal import Decimal

from flask import Blueprint, request, jsonify
from flask_jwt_extended import jwt_required, get_jwt_identity

from app.extensions import db
from app.models import Address
from app.utils.geo import CoordinateError, validate_coords


address_bp = Blueprint(
    "addresses",
    __name__,
    url_prefix="/api/addresses"
)


def _serialize(address):
    return {
        "id": address.id,
        "label": address.label,
        "recipient_name": address.recipient_name,
        "phone": address.phone,
        "address_line": address.address_line,
        "city": address.city,
        "delivery_instructions": address.delivery_instructions,
        "is_default": address.is_default,
        "latitude": (
            float(address.latitude)
            if address.latitude is not None
            else None
        ),
        "longitude": (
            float(address.longitude)
            if address.longitude is not None
            else None
        ),
    }


def _apply_coords(address, data):
    """Set / clear the address pin if the request mentions coordinates.

    Same rules as Store: both together or neither, valid ranges. Raises
    ``CoordinateError``.
    """
    if "latitude" not in data and "longitude" not in data:
        return
    lat, lng = validate_coords(data.get("latitude"), data.get("longitude"))
    if lat is None:
        address.latitude = None
        address.longitude = None
    else:
        address.latitude = Decimal(str(lat)).quantize(Decimal("0.000001"))
        address.longitude = Decimal(str(lng)).quantize(Decimal("0.000001"))


@address_bp.route("", methods=["GET"])
@jwt_required()
def get_addresses():
    current_user_id = int(get_jwt_identity())

    addresses = Address.query.filter_by(
        user_id=current_user_id
    ).order_by(
        Address.is_default.desc(),
        Address.created_at.desc()
    ).all()

    return jsonify({
        "addresses": [_serialize(address) for address in addresses]
    }), 200


@address_bp.route("", methods=["POST"])
@jwt_required()
def create_address():
    current_user_id = int(get_jwt_identity())

    data = request.get_json() or {}

    label = data.get("label")
    recipient_name = data.get("recipient_name")
    phone = data.get("phone")
    address_line = data.get("address_line")
    city = data.get("city")
    delivery_instructions = data.get("delivery_instructions")
    is_default = data.get("is_default", False)

    if not all([
        label,
        recipient_name,
        phone,
        address_line,
        city
    ]):
        return jsonify({
            "message": (
                "Label, recipient name, phone, "
                "address, and city are required"
            )
        }), 400

    # If this address is marked as default,
    # remove the default status from existing addresses.
    if is_default:
        Address.query.filter_by(
            user_id=current_user_id,
            is_default=True
        ).update({
            "is_default": False
        })

    # If this is the customer's first address,
    # automatically make it the default.
    existing_addresses = Address.query.filter_by(
        user_id=current_user_id
    ).count()

    if existing_addresses == 0:
        is_default = True

    new_address = Address(
        user_id=current_user_id,
        label=label.strip(),
        recipient_name=recipient_name.strip(),
        phone=phone.strip(),
        address_line=address_line.strip(),
        city=city.strip(),
        delivery_instructions=(
            delivery_instructions.strip()
            if delivery_instructions
            else None
        ),
        is_default=bool(is_default)
    )

    try:
        _apply_coords(new_address, data)
    except CoordinateError as exc:
        return jsonify({"message": str(exc)}), 400

    db.session.add(new_address)
    db.session.commit()

    return jsonify({
        "message": "Address added successfully",
        "address": _serialize(new_address),
    }), 201


@address_bp.route("/<int:address_id>", methods=["GET"])
@jwt_required()
def get_address(address_id):
    current_user_id = int(get_jwt_identity())

    address = Address.query.filter_by(
        id=address_id,
        user_id=current_user_id
    ).first()

    if not address:
        return jsonify({
            "message": "Address not found"
        }), 404

    return jsonify({"address": _serialize(address)}), 200


@address_bp.route("/<int:address_id>", methods=["PUT"])
@jwt_required()
def update_address(address_id):
    current_user_id = int(get_jwt_identity())

    address = Address.query.filter_by(
        id=address_id,
        user_id=current_user_id
    ).first()

    if not address:
        return jsonify({
            "message": "Address not found"
        }), 404

    data = request.get_json() or {}

    label = data.get("label")
    recipient_name = data.get("recipient_name")
    phone = data.get("phone")
    address_line = data.get("address_line")
    city = data.get("city")
    delivery_instructions = data.get("delivery_instructions")
    is_default = data.get("is_default", address.is_default)

    if not all([
        label,
        recipient_name,
        phone,
        address_line,
        city
    ]):
        return jsonify({
            "message": (
                "Label, recipient name, phone, "
                "address, and city are required"
            )
        }), 400

    if is_default:
        Address.query.filter(
            Address.user_id == current_user_id,
            Address.id != address_id,
            Address.is_default.is_(True)
        ).update({
            "is_default": False
        })

    address.label = label.strip()
    address.recipient_name = recipient_name.strip()
    address.phone = phone.strip()
    address.address_line = address_line.strip()
    address.city = city.strip()
    address.delivery_instructions = (
        delivery_instructions.strip()
        if delivery_instructions
        else None
    )
    address.is_default = bool(is_default)

    try:
        _apply_coords(address, data)
    except CoordinateError as exc:
        return jsonify({"message": str(exc)}), 400

    db.session.commit()

    return jsonify({
        "message": "Address updated successfully",
        "address": _serialize(address),
    }), 200


@address_bp.route("/<int:address_id>", methods=["DELETE"])
@jwt_required()
def delete_address(address_id):
    current_user_id = int(get_jwt_identity())

    address = Address.query.filter_by(
        id=address_id,
        user_id=current_user_id
    ).first()

    if not address:
        return jsonify({
            "message": "Address not found"
        }), 404

    was_default = address.is_default

    db.session.delete(address)
    db.session.commit()

    # If the deleted address was the default,
    # make the newest remaining address the default.
    if was_default:
        replacement = Address.query.filter_by(
            user_id=current_user_id
        ).order_by(
            Address.created_at.desc()
        ).first()

        if replacement:
            replacement.is_default = True
            db.session.commit()

    return jsonify({
        "message": "Address deleted successfully"
    }), 200


@address_bp.route("/<int:address_id>/default", methods=["PATCH"])
@jwt_required()
def set_default_address(address_id):
    current_user_id = int(get_jwt_identity())

    address = Address.query.filter_by(
        id=address_id,
        user_id=current_user_id
    ).first()

    if not address:
        return jsonify({
            "message": "Address not found"
        }), 404

    Address.query.filter_by(
        user_id=current_user_id,
        is_default=True
    ).update({
        "is_default": False
    })

    address.is_default = True

    db.session.commit()

    return jsonify({
        "message": "Default address updated successfully",
        "address": _serialize(address),
    }), 200
