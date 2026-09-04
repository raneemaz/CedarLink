from datetime import datetime

from app.extensions import db


class ShoppingPreferences(db.Model):
    __tablename__ = "shopping_preferences"

    id = db.Column(db.Integer, primary_key=True)

    user_id = db.Column(
        db.Integer,
        db.ForeignKey("users.id"),
        nullable=False,
        unique=True,
    )

    # Pre-fill the checkout address/city from the user's default saved
    # address when one exists.
    autofill_default_address = db.Column(
        db.Boolean,
        nullable=False,
        default=True,
        server_default=db.true(),
    )

    # Which payment option checkout preselects.
    preferred_payment_method = db.Column(
        db.Enum("card", "cash_on_delivery"),
        nullable=False,
        default="cash_on_delivery",
        server_default="cash_on_delivery",
    )

    # Optional fallback city for the checkout city selector.
    default_delivery_city = db.Column(db.String(100), nullable=True)

    # Hide products with no stock from the product listing.
    hide_out_of_stock = db.Column(
        db.Boolean,
        nullable=False,
        default=False,
        server_default=db.false(),
    )

    created_at = db.Column(
        db.DateTime,
        default=datetime.utcnow,
        nullable=False,
    )

    updated_at = db.Column(
        db.DateTime,
        default=datetime.utcnow,
        onupdate=datetime.utcnow,
        nullable=False,
    )

    user = db.relationship(
        "User",
        back_populates="shopping_preferences",
    )

    # Explicitly chosen categories, in the customer's own order. Ordered
    # by position so the home page can render them without re-sorting.
    interests = db.relationship(
        "ShoppingInterest",
        back_populates="preferences",
        cascade="all, delete-orphan",
        order_by="ShoppingInterest.position",
        lazy="selectin",
    )

    @property
    def interest_category_ids(self):
        return [interest.category_id for interest in self.interests]

    def to_dict(self):
        return {
            "autofill_default_address": self.autofill_default_address,
            "preferred_payment_method": self.preferred_payment_method,
            "default_delivery_city": self.default_delivery_city,
            "hide_out_of_stock": self.hide_out_of_stock,
            "interest_category_ids": self.interest_category_ids,
        }
