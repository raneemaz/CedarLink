from datetime import datetime, timezone

from app.extensions import db


def _utc_now():
    """Timezone-aware UTC now — never ``datetime.utcnow`` (CLAUDE.md)."""
    return datetime.now(timezone.utc)


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
    #
    # "card" is genuinely reachable, so this is not a preference for
    # something that cannot happen: POST /api/payment-methods saves a card,
    # the settings page offers both options, and Checkout preselects the
    # default card when this says "card". validate_checkout_payment_method
    # accepts it and the order is created.
    #
    # What it does NOT do is charge anything. Checkout creates no Payment
    # row and calls no provider — POST /api/payments is a separate endpoint
    # nothing invokes during checkout. So choosing a card today records an
    # intent and collects on delivery all the same. Worth knowing before
    # anyone reads this column as evidence that card payment is wired up.
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
        default=_utc_now,
        nullable=False,
    )

    updated_at = db.Column(
        db.DateTime,
        default=_utc_now,
        onupdate=_utc_now,
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
        """Chosen category ids, in the customer's own order.

        Sorted here rather than trusting the relationship's ``order_by``:
        that only orders the collection as it is loaded, and reordering an
        existing set now updates ``position`` in place, so between the
        update and the next load the loaded order is stale.
        """
        return [
            interest.category_id
            for interest in sorted(
                self.interests, key=lambda interest: interest.position
            )
        ]

    def to_dict(self):
        return {
            "autofill_default_address": self.autofill_default_address,
            "preferred_payment_method": self.preferred_payment_method,
            "default_delivery_city": self.default_delivery_city,
            "hide_out_of_stock": self.hide_out_of_stock,
            "interest_category_ids": self.interest_category_ids,
        }
