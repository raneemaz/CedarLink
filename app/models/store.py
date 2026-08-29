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

    is_active = db.Column(
        db.Boolean,
        default=True,
        nullable=False
    )

    inside_city_delivery_fee = db.Column(
        db.Numeric(10, 2),
        nullable=False,
        default=0.00
    )

    outside_city_delivery_fee = db.Column(
        db.Numeric(10, 2),
        nullable=False,
        default=0.00
    )

    delivery_available = db.Column(
        db.Boolean,
        default=True,
        nullable=False
    )

    owner = db.relationship(
        "User",
        back_populates="stores"
    )

    products = db.relationship(
        "Product",
        back_populates="store",
        cascade="all, delete-orphan"
    )

    orders = db.relationship(
        "Order",
        back_populates="store",
        cascade="all, delete-orphan"
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
            "inside_city_delivery_fee": float(self.inside_city_delivery_fee
                                              or 0),
            "outside_city_delivery_fee": float(self.outside_city_delivery_fee
                                               or 0),
            "delivery_available": self.delivery_available,
        }
