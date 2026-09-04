"""The product-card payload, in one place.

``ProductCard`` on the client reads one shape, and it is now built by two
endpoints — the product listing and the home page's category sections. A
second hand-written copy of the same dict is how the two drift, so there
is one function and both call it.

Translations: every language goes on the wire and the client picks (ADR
0012), so nothing here is locale-dependent.
"""

from app.utils.file_utils import product_image_url

LANGUAGES = ("en", "ar", "fr")


def translation_fields(product):
    """name_en/ar/fr + description_en/ar/fr, plus ``name`` / ``description``
    as English-canonical aliases for any consumer that is not yet
    language-aware."""
    fields = {
        f"{base}_{lang}": getattr(product, f"{base}_{lang}")
        for base in ("name", "description")
        for lang in LANGUAGES
    }
    fields["name"] = product.name_en
    fields["description"] = product.description_en
    return fields


def rating_fields(entity):
    """``rating_avg`` (float or None) + ``rating_count`` for a product/store."""
    return {
        "rating_avg": (
            float(entity.rating_avg)
            if entity.rating_avg is not None
            else None
        ),
        "rating_count": entity.rating_count or 0,
    }


def product_card(product):
    """One product as the storefront grid renders it."""
    first_image = product.images[0].image_url if product.images else None

    return {
        "id": product.id,
        "price": float(product.price),
        "stock": product.stock,
        "store_id": product.store_id,
        "store_name": product.store.name,
        "category_id": product.category_id,
        "image": product_image_url(first_image),
        **translation_fields(product),
        **rating_fields(product),
    }
