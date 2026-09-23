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


def _option_value_payload(value):
    return {
        "id": value.id,
        "value": value.value_en,
        "value_en": value.value_en,
        "value_ar": value.value_ar,
        "value_fr": value.value_fr,
        "display_order": value.display_order,
    }


def _variant_payload(product, variant):
    # Resolved price: the variant's own when it set one, else the product's
    # (ADR 0035). float only at this JSON boundary. price_override is kept
    # separate so the vendor form can tell "same as product" from "set".
    resolved = variant.price if variant.price is not None else product.price
    return {
        "id": variant.id,
        "sku": variant.sku,
        "price": float(resolved),
        "price_override": (
            float(variant.price) if variant.price is not None else None
        ),
        "stock": variant.stock,
        "is_active": variant.is_active,
        "option_value_ids": sorted(
            link.option_value_id for link in variant.values
        ),
        "label": variant.label("en"),
        "label_en": variant.label("en"),
        "label_ar": variant.label("ar"),
        "label_fr": variant.label("fr"),
    }


def variant_fields(product, include_inactive=False):
    """``options`` + ``variants`` for the product detail payload — an empty
    dict when the product has no options, so a plain product serializes
    byte-for-byte as it did before this feature (ADR 0035). Not included on
    the grid card.

    ``include_inactive`` — the vendor's own edit view needs the retired
    variants to manage them; the public product page must not show a
    variant a customer could then try to pick (ADR 0036). Options and
    their values are always returned in full: a value no active variant
    uses simply won't resolve, and the picker marks that combination
    unavailable.
    """
    if not product.options:
        return {}

    variants = product.variants
    if not include_inactive:
        variants = [v for v in variants if v.is_active]

    return {
        "options": [
            {
                "id": option.id,
                "name": option.name_en,
                "name_en": option.name_en,
                "name_ar": option.name_ar,
                "name_fr": option.name_fr,
                "display_order": option.display_order,
                "values": [
                    _option_value_payload(value) for value in option.values
                ],
            }
            for option in product.options
        ],
        "variants": [
            _variant_payload(product, variant) for variant in variants
        ],
    }


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


def sellable_stock(product):
    """How many units a customer could actually buy right now.

    ADR 0035: once a product has active variants, ``products.stock`` stops
    being consulted for purchasing it — the variant rows are authoritative.
    The card went on reporting the column anyway, so a product whose stock
    had moved onto its variants advertised 0 while its units sat behind the
    option picker, and the "in stock only" filter hid it from the grid
    outright. Retired variants are excluded because they cannot be bought.

    Reads ``product.variants``, which the listing and the home sections
    both eager-load, so this adds no query.
    """
    active = [variant for variant in product.variants if variant.is_active]

    if active:
        return sum(variant.stock for variant in active)

    return product.stock


def product_card(product):
    """One product as the storefront grid renders it."""
    first_image = product.images[0].image_url if product.images else None

    return {
        "id": product.id,
        "price": float(product.price),
        "stock": sellable_stock(product),
        "store_id": product.store_id,
        "store_name": product.store.name,
        "category_id": product.category_id,
        "image": product_image_url(first_image),
        # The vendor list shows a "N variants" chip; the grid card does not
        # carry the options/variants themselves (ADR 0036).
        "variant_count": len(product.variants),
        "has_variants": len(product.variants) > 0,
        **translation_fields(product),
        **rating_fields(product),
    }
