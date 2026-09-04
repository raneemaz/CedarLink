"""Shopping preferences: storage helpers, validation, and interest order.

These preferences affect the checkout pre-fill, the product listing, and
the order of the home page's category sections. They never change
checkout, order, or payment logic.

**Interests are stated, never inferred.** A customer picks up to five
categories and the home page leads with them. Nothing here reads a search
history, a view count, or a purchase — there is no such data and none is
collected. At this volume a learned recommender would return noise, and
every position in the resulting order can be explained in one sentence.
See docs/decisions/0022-customer-interests.md.
"""

from datetime import datetime

from sqlalchemy import func, select

from app.extensions import db
from app.models.category import Category
from app.models.product import Product
from app.models.shopping_interest import ShoppingInterest
from app.models.shopping_preferences import ShoppingPreferences
from app.models.store import Store

CHECKOUT_METHODS = {"card", "cash_on_delivery"}
BOOLEAN_KEYS = {"autofill_default_address", "hide_out_of_stock"}
PREFERENCE_KEYS = BOOLEAN_KEYS | {
    "preferred_payment_method",
    "default_delivery_city",
    "interest_category_ids",
}

MAX_CITY_LENGTH = 100

# Five is a deliberate ceiling, not a storage limit. A customer who picks
# everything has expressed no preference, and a home page whose first
# screen is "all of it" is the one this feature exists to replace.
MAX_INTERESTS = 5


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
        "interest_category_ids": prefs.interest_category_ids,
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

    if "interest_category_ids" in data:
        ok, error = _apply_interests(prefs, data["interest_category_ids"])
        if not ok:
            return False, error

    prefs.updated_at = datetime.utcnow()

    return True, None


def _apply_interests(prefs, value):
    """Replace the interest set. Returns ``(ok, error_message)``.

    Replace rather than merge: the settings form sends the whole list, so
    a merge would make deselecting the last category impossible.
    """
    if value is None:
        value = []

    if not isinstance(value, list):
        return False, "interest_category_ids must be a list"

    if len(value) > MAX_INTERESTS:
        return (
            False,
            f"Choose at most {MAX_INTERESTS} interests",
        )

    ids = []

    for raw in value:
        # Booleans are ints in Python; a `true` here is a client bug, not
        # a category id.
        if isinstance(raw, bool) or not isinstance(raw, int):
            return False, "interest_category_ids must contain category ids"
        if raw in ids:
            return False, "interest_category_ids must not repeat a category"
        ids.append(raw)

    if ids:
        found = set(
            db.session.execute(
                select(Category.id).where(Category.id.in_(ids))
            ).scalars()
        )
        missing = [cid for cid in ids if cid not in found]
        if missing:
            return (
                False,
                "Unknown category ids: "
                + ", ".join(str(cid) for cid in missing),
            )

    prefs.interests.clear()

    for position, category_id in enumerate(ids):
        prefs.interests.append(
            ShoppingInterest(category_id=category_id, position=position)
        )

    return True, None


# --------------------------------------------------------------------------- #
# Home ordering — stated interests first, then a stable default
# --------------------------------------------------------------------------- #

def _default_category_order():
    """Categories with the most visible products first, then by name.

    The fallback for a customer who has chosen nothing, and for signed-out
    visitors. Busiest-first is the honest guess when nobody has said
    anything: it is the order most likely to have something to show, and
    it needs no history to compute. The name tiebreak keeps it stable
    rather than letting equal counts shuffle between requests.
    """
    counts = (
        select(
            Category.id,
            func.count(Product.id).label("product_count"),
        )
        .select_from(Category)
        .outerjoin(
            Product,
            db.and_(
                Product.category_id == Category.id,
                Product.deleted_at.is_(None),
            ),
        )
        .outerjoin(
            Store,
            db.and_(
                Store.id == Product.store_id,
                Store.deleted_at.is_(None),
                Store.is_active.is_(True),
                Store.approval_status == "approved",
            ),
        )
        .group_by(Category.id)
        .subquery()
    )

    rows = db.session.execute(
        select(Category)
        .join(counts, counts.c.id == Category.id)
        .order_by(counts.c.product_count.desc(), Category.name_en)
    ).scalars()

    return list(rows)


def hides_out_of_stock(user_id):
    """Whether this user asked not to be shown sold-out products.

    Read-only, and never creates a row: a product listing is a GET, and a
    GET must not write. A user with no preferences row has not asked for
    anything, which is the same answer as False.
    """
    if user_id is None:
        return False

    prefs = ShoppingPreferences.query.filter_by(user_id=user_id).first()

    return bool(prefs and prefs.hide_out_of_stock)


def has_interests(user_id):
    """Whether this user has stated any interest.

    Lets the home page say why it is in the order it is in. Never creates
    a row — asking the question must not be a write.
    """
    if user_id is None:
        return False

    prefs = ShoppingPreferences.query.filter_by(user_id=user_id).first()

    return bool(prefs and prefs.interests)


def ordered_categories(user_id):
    """Every category, the customer's stated interests first.

    Interests keep the order the customer put them in; everything else
    follows in the default order. Nothing is hidden — an interest moves a
    category up the page, it never removes one.

    ``user_id`` may be None for a signed-out visitor, who gets the default
    order. No row is created as a side effect of reading.
    """
    default_order = _default_category_order()

    if user_id is None:
        return default_order

    prefs = ShoppingPreferences.query.filter_by(user_id=user_id).first()

    if prefs is None or not prefs.interests:
        return default_order

    by_id = {category.id: category for category in default_order}

    chosen = [
        by_id[interest.category_id]
        for interest in prefs.interests
        if interest.category_id in by_id
    ]
    chosen_ids = {category.id for category in chosen}

    return chosen + [
        category for category in default_order
        if category.id not in chosen_ids
    ]
