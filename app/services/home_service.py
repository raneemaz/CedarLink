"""The home page's category sections, in the viewer's interest order.

One endpoint rather than one request per category: the ordering rule lives
in ``shopping_preferences_service`` and the client only renders what it is
given, so a signed-out visitor and a customer with five interests take the
same code path.
"""

from sqlalchemy import select
from sqlalchemy.orm import selectinload

from app.extensions import db
from app.models.product import Product
from app.models.store import Store
from app.services import shopping_preferences_service
from app.utils.product_payload import product_card

# How many products a section shows before "view all".
SECTION_SIZE = 4

# How many sections the page renders. Interests come first, so a customer
# with five picks sees exactly their five.
MAX_SECTIONS = 6


def _visible_products(category_id, limit):
    """Newest visible products in one category.

    Same visibility rule as the product listing: not soft-deleted, and
    belonging to a store that is live and approved.
    """
    return list(
        db.session.execute(
            select(Product)
            .join(Store, Store.id == Product.store_id)
            .where(
                Product.category_id == category_id,
                Product.deleted_at.is_(None),
                Store.deleted_at.is_(None),
                Store.is_active.is_(True),
                Store.approval_status == "approved",
            )
            .options(selectinload(Product.images))
            .order_by(Product.id.desc())
            .limit(limit)
        ).scalars()
    )


def home_sections(user_id, language="en"):
    """``[{category, products}]`` for the home page.

    Empty categories are dropped *after* ordering, not before: a customer
    who asked for a category with nothing in it should not silently have
    another one promoted into its place without the order being honoured
    for everything else.
    """
    categories = shopping_preferences_service.ordered_categories(user_id)

    sections = []

    for category in categories:
        if len(sections) >= MAX_SECTIONS:
            break

        products = _visible_products(category.id, SECTION_SIZE)

        if not products:
            continue

        sections.append({"category": category, "products": products})

    return sections


def serialize_sections(sections, language="en"):
    """JSON for the home page.

    Categories carry every translation and the client picks (ADR 0012);
    ``language`` only chooses the sort-independent display name used by a
    consumer that is not language-aware.
    """
    return [
        {
            "category": {
                **section["category"].to_dict(),
                "display_name": section["category"].localized_name(language),
            },
            "products": [
                product_card(product) for product in section["products"]
            ],
        }
        for section in sections
    ]
