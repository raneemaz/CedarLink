"""Shopping preferences: storage helpers and validation.

These preferences affect the checkout pre-fill and the product listing. They
never change checkout, order, or payment logic.
"""

from datetime import datetime

from app.extensions import db
from app.models.shopping_preferences import ShoppingPreferences

CHECKOUT_METHODS = {"card", "cash_on_delivery"}
BOOLEAN_KEYS = {"autofill_default_address", "hide_out_of_stock"}
PREFERENCE_KEYS = BOOLEAN_KEYS | {
    "preferred_payment_method",
    "default_delivery_city",
}

MAX_CITY_LENGTH = 100


def get_or_create_preferences(user_id):
    """Return the user's shopping preferences, creating a default row if none."""
    prefs = ShoppingPreferences.query.filter_by(user_id=user_id).first()

    if prefs is None:
        prefs = ShoppingPreferences(user_id=user_id)
        db.session.add(prefs)
        db.session.commit()

    return prefs


def serialize_preferences(prefs):
    return {
        "autofill_default_address": prefs.autofill_default_address,
        "preferred_payment_method": prefs.preferred_payment_method,
        "default_delivery_city": prefs.default_delivery_city,
        "hide_out_of_stock": prefs.hide_out_of_stock,
    }


def apply_preference_updates(prefs, data):
    """Apply only the provided, valid keys. Returns ``(ok, error_message)``."""
    if not isinstance(data, dict):
        return False, "Request body must be a JSON object"

    unknown = set(data) - PREFERENCE_KEYS

    if unknown:
        return (
            False,
            "Unknown preference keys: " + ", ".join(sorted(unknown)),
        )

    for key in BOOLEAN_KEYS:
        if key in data:
            if not isinstance(data[key], bool):
                return False, f"'{key}' must be true or false"
            setattr(prefs, key, data[key])

    if "preferred_payment_method" in data:
        value = data["preferred_payment_method"]
        if value not in CHECKOUT_METHODS:
            return (
                False,
                "preferred_payment_method must be one of: "
                + ", ".join(sorted(CHECKOUT_METHODS)),
            )
        prefs.preferred_payment_method = value

    if "default_delivery_city" in data:
        value = data["default_delivery_city"]
        if value is None or value == "":
            prefs.default_delivery_city = None
        elif not isinstance(value, str):
            return False, "default_delivery_city must be a string or null"
        elif len(value.strip()) > MAX_CITY_LENGTH:
            return (
                False,
                f"default_delivery_city must be at most {MAX_CITY_LENGTH} "
                "characters",
            )
        else:
            prefs.default_delivery_city = value.strip()

    prefs.updated_at = datetime.utcnow()

    return True, None
