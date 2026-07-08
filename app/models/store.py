from app.extensions import db
from flask import jsonify, request
from flask_jwt_extended import jwt_required, get_jwt_identity


class Store(db.Model):
    __tablename__ = "stores"

    id = db.Column(db.Integer, primary_key=True)

    owner_id = db.Column(
        db.Integer,
        db.ForeignKey("users.id"),
        nullable=False
    )

    name = db.Column(db.String(120), nullable=False)

    description = db.Column(db.Text)

    location = db.Column(db.String(255))

    contact_info = db.Column(db.String(255))

    is_active = db.Column(
        db.Boolean,
        default=True,
        nullable=False
    )

    # Phase J — Delivery settings
    delivery_fee = db.Column(
        db.Numeric(10, 2),
        default=0.00,
        nullable=False
    )

    delivery_available = db.Column(
        db.Boolean,
        default=True,
        nullable=False
    )

    owner = db.relationship(
        "User",
        backref=db.backref("stores", lazy=True)
    )

    def to_dict(self):
        return {
            "id": self.id,
            "owner_id": self.owner_id,
            "name": self.name,
            "description": self.description,
            "location": self.location,
            "contact_info": self.contact_info,
            "is_active": self.is_active,
            "delivery_fee": float(self.delivery_fee or 0),
            "delivery_available": self.delivery_available,
        }


@jwt_required()
def update_store(store_id):
    user_id = int(get_jwt_identity())
    store = db.session.get(Store, store_id)

    if not store:
        return jsonify({"message": "Store not found"}), 404

    if store.owner_id != user_id:
        return jsonify({"message": "Not allowed"}), 403

    data = request.get_json() or {}

    store.name = data.get("name", store.name)
    store.description = data.get(
        "description",
        store.description
    )
    store.location = data.get(
        "location",
        store.location
    )
    store.contact_info = data.get(
        "contact_info",
        store.contact_info
    )

    # Phase J — update delivery settings
    if "delivery_fee" in data:
        try:
            delivery_fee = float(data["delivery_fee"])

            if delivery_fee < 0:
                return jsonify({
                    "message": "Delivery fee cannot be negative"
                }), 400

            store.delivery_fee = delivery_fee

        except (TypeError, ValueError):
            return jsonify({
                "message": "Invalid delivery fee"
            }), 400

    if "delivery_available" in data:
        if not isinstance(data["delivery_available"], bool):
            return jsonify({
                "message": "delivery_available must be true or false"
            }), 400

        store.delivery_available = data["delivery_available"]

    db.session.commit()

    return jsonify({
        "message": "Store updated successfully",
        "store": store.to_dict()
    }), 200


@jwt_required()
def toggle_store_status(store_id):
    user_id = int(get_jwt_identity())
    store = db.session.get(Store, store_id)

    if not store:
        return jsonify({"message": "Store not found"}), 404

    if store.owner_id != user_id:
        return jsonify({"message": "Not allowed"}), 403

    store.is_active = not store.is_active
    db.session.commit()

    return jsonify({
        "message": "Store status updated",
        "is_active": store.is_active
    }), 200
