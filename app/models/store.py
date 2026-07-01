from app.extensions import db


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

    is_active = db.Column(db.Boolean, default=True)

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
        }


@store_bp.route("/<int:store_id>", methods=["PUT"])
@jwt_required()
def update_store(store_id):
    user_id = get_jwt_identity()
    store = Store.query.get(store_id)

    if not store:
        return jsonify({"message": "Store not found ❌"}), 404

    # ownership check (we enforce in 5.9 too, but here early)
    if not check_owner(store, user_id):
        return jsonify({"message": "Not allowed ❌"}), 403

    data = request.get_json()

    store.name = data.get("name", store.name)
    store.description = data.get("description", store.description)
    store.location = data.get("location", store.location)
    store.contact_info = data.get("contact_info", store.contact_info)

    db.session.commit()

    return jsonify({
        "message": "Store updated successfully ✅",
        "store": store.to_dict()
    }), 200


@store_bp.route("/<int:store_id>/status", methods=["PATCH"])
@jwt_required()
def toggle_store_status(store_id):
    user_id = get_jwt_identity()
    store = Store.query.get(store_id)

    if not store:
        return jsonify({"message": "Store not found ❌"}), 404

    if store.owner_id != user_id:
        return jsonify({"message": "Not allowed ❌"}), 403

    store.is_active = not store.is_active
    db.session.commit()

    return jsonify({
        "message": "Store status updated ✅",
        "is_active": store.is_active
    }), 200

