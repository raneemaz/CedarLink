from flask import Blueprint, request, jsonify
from flask_jwt_extended import jwt_required, get_jwt_identity

from app.extensions import db
from app.models import Address


address_bp = Blueprint(
    "addresses",
    __name__,
    url_prefix="/api/addresses"
)


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
        "addresses": [
            {
                "id": address.id,
                "label": address.label,
                "recipient_name": address.recipient_name,
                "phone": address.phone,
                "address_line": address.address_line,
                "city": address.city,
                "delivery_instructions": address.delivery_instructions,
                "is_default": address.is_default
            }
            for address in addresses
        ]
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

    db.session.add(new_address)
    db.session.commit()

    return jsonify({
        "message": "Address added successfully",
        "address": {
            "id": new_address.id,
            "label": new_address.label,
            "recipient_name": new_address.recipient_name,
            "phone": new_address.phone,
            "address_line": new_address.address_line,
            "city": new_address.city,
            "delivery_instructions": new_address.delivery_instructions,
            "is_default": new_address.is_default
        }
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

    return jsonify({
        "address": {
            "id": address.id,
            "label": address.label,
            "recipient_name": address.recipient_name,
            "phone": address.phone,
            "address_line": address.address_line,
            "city": address.city,
            "delivery_instructions": address.delivery_instructions,
            "is_default": address.is_default
        }
    }), 200


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

    db.session.commit()

    return jsonify({
        "message": "Address updated successfully",
        "address": {
            "id": address.id,
            "label": address.label,
            "recipient_name": address.recipient_name,
            "phone": address.phone,
            "address_line": address.address_line,
            "city": address.city,
            "delivery_instructions": address.delivery_instructions,
            "is_default": address.is_default
        }
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
        "address": {
            "id": address.id,
            "label": address.label,
            "recipient_name": address.recipient_name,
            "phone": address.phone,
            "address_line": address.address_line,
            "city": address.city,
            "delivery_instructions": address.delivery_instructions,
            "is_default": address.is_default
        }
    }), 200
