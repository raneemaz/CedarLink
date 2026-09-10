"""Vendor-side CRUD for product options, option values and variants (V-2).

V-1 (ADR 0035) built the schema and the pricing/stock split; the only way
to create a ``variant_id`` was a raw SQL insert or the seed. This is the
management layer behind ``product_variant_routes`` — one function per
operation, each taking the already-loaded, already-ownership-checked
``product``. Route handlers parse the request and translate
``ProductVariantError`` into the one error shape; the rules live here.

See docs/decisions/0036-variant-management-and-picker.md.
"""

from decimal import Decimal, InvalidOperation

from app.extensions import db
from app.models.order_item import OrderItem
from app.models.product_option import ProductOption
from app.models.product_option_value import ProductOptionValue
from app.models.product_variant import ProductVariant
from app.models.product_variant_value import ProductVariantValue

_LANGUAGES = ("en", "ar", "fr")


class ProductVariantError(Exception):
    """A management operation that failed a rule.

    Same shape as ``order_service.OrderError``: carries the HTTP status and
    the JSON body the route returns verbatim.
    """

    def __init__(self, message, status_code=400, **extra):
        super().__init__(message)
        self.status_code = status_code
        self.payload = {"error": message, **extra}


# --------------------------------------------------------------------------- #
# Request-body helpers
# --------------------------------------------------------------------------- #

def _read_trilingual(data, base, *, require_en):
    """``{base}_en/ar/fr`` out of a request body.

    Mirrors ``product_routes._read_translations``: English is required on
    create and cannot be blanked; a blank ar/fr clears that optional
    translation; only keys present are touched on update.
    """
    values = {}

    for lang in _LANGUAGES:
        key = f"{base}_{lang}"
        if key not in data:
            continue

        raw = data[key]
        if raw is None or (isinstance(raw, str) and not raw.strip()):
            if lang == "en":
                raise ProductVariantError(f"{base}_en cannot be blank")
            values[key] = None
        elif isinstance(raw, str):
            values[key] = raw.strip()
        else:
            raise ProductVariantError(f"{key} must be a string")

    if require_en and f"{base}_en" not in values:
        raise ProductVariantError(f"{base}_en is required")

    return values


def _read_display_order(data):
    if "display_order" not in data or data["display_order"] is None:
        return 0
    try:
        return int(data["display_order"])
    except (TypeError, ValueError):
        raise ProductVariantError("display_order must be an integer")


def _read_price(data):
    """``None`` (fall back to the product) when absent or blank, else a
    non-negative ``Decimal``."""
    if "price" not in data or data["price"] in (None, ""):
        return None
    try:
        price = Decimal(str(data["price"]))
    except (InvalidOperation, TypeError):
        raise ProductVariantError("Price must be a number")
    if price < 0:
        raise ProductVariantError("Price cannot be negative")
    return price


def _read_stock(data, *, required):
    if "stock" not in data or data["stock"] in (None, ""):
        if required:
            raise ProductVariantError("Stock is required")
        return None
    try:
        stock = int(data["stock"])
    except (TypeError, ValueError):
        raise ProductVariantError("Stock must be an integer")
    if stock < 0:
        raise ProductVariantError("Stock cannot be negative")
    return stock


# --------------------------------------------------------------------------- #
# Lookups — scoped to the product, so a foreign id is a 404 not a leak
# --------------------------------------------------------------------------- #

def _get_option(product, option_id):
    option = db.session.get(ProductOption, option_id)
    if option is None or option.product_id != product.id:
        raise ProductVariantError("Option not found", 404)
    return option


def _get_value(product, option_id, value_id):
    option = _get_option(product, option_id)
    value = db.session.get(ProductOptionValue, value_id)
    if value is None or value.option_id != option.id:
        raise ProductVariantError("Option value not found", 404)
    return value


def _get_variant(product, variant_id):
    variant = db.session.get(ProductVariant, variant_id)
    if variant is None or variant.product_id != product.id:
        raise ProductVariantError("Variant not found", 404)
    return variant


# --------------------------------------------------------------------------- #
# Options
# --------------------------------------------------------------------------- #

def add_option(product, data):
    names = _read_trilingual(data, "name", require_en=True)
    option = ProductOption(
        product_id=product.id,
        display_order=_read_display_order(data),
        **names,
    )
    db.session.add(option)
    db.session.commit()
    return option


def update_option(product, option_id, data):
    option = _get_option(product, option_id)
    for column, value in _read_trilingual(
        data, "name", require_en=False
    ).items():
        setattr(option, column, value)
    if "display_order" in data:
        option.display_order = _read_display_order(data)
    db.session.commit()
    return option


def delete_option(product, option_id):
    option = _get_option(product, option_id)
    value_ids = [value.id for value in option.values]
    if value_ids and _values_in_use(value_ids):
        raise ProductVariantError(
            "Remove the variants that use this option before deleting it.",
            409,
            code="option_in_use",
        )
    db.session.delete(option)
    db.session.commit()


# --------------------------------------------------------------------------- #
# Option values
# --------------------------------------------------------------------------- #

def add_value(product, option_id, data):
    option = _get_option(product, option_id)
    values = _read_trilingual(data, "value", require_en=True)
    value = ProductOptionValue(
        option_id=option.id,
        display_order=_read_display_order(data),
        **values,
    )
    db.session.add(value)
    db.session.commit()
    return value


def update_value(product, option_id, value_id, data):
    value = _get_value(product, option_id, value_id)
    for column, new in _read_trilingual(
        data, "value", require_en=False
    ).items():
        setattr(value, column, new)
    if "display_order" in data:
        value.display_order = _read_display_order(data)
    db.session.commit()
    return value


def delete_value(product, option_id, value_id):
    value = _get_value(product, option_id, value_id)
    if _values_in_use([value.id]):
        raise ProductVariantError(
            "Remove the variants that use this value before deleting it.",
            409,
            code="value_in_use",
        )
    db.session.delete(value)
    db.session.commit()


def _values_in_use(value_ids):
    return (
        db.session.query(ProductVariantValue.id)
        .filter(ProductVariantValue.option_value_id.in_(value_ids))
        .first()
        is not None
    )


# --------------------------------------------------------------------------- #
# Variants
# --------------------------------------------------------------------------- #

def _validated_option_value_ids(product, raw_ids):
    """The de-duplicated set of option-value ids for a new/edited variant,
    after checking they name exactly one value on each of this product's
    own option axes."""
    if not isinstance(raw_ids, list) or not raw_ids:
        raise ProductVariantError("option_value_ids is required")
    try:
        ids = {int(x) for x in raw_ids}
    except (TypeError, ValueError):
        raise ProductVariantError("option_value_ids must be integers")

    product_option_ids = {option.id for option in product.options}
    if not product_option_ids:
        raise ProductVariantError(
            "Add an option to this product before creating a variant.",
            400,
            code="no_options",
        )

    values = (
        ProductOptionValue.query
        .filter(ProductOptionValue.id.in_(ids))
        .all()
    )
    if len(values) != len(ids):
        raise ProductVariantError("Unknown option value", 404)

    for value in values:
        if value.option_id not in product_option_ids:
            raise ProductVariantError(
                "That option value is not on this product", 400
            )

    axes = [value.option_id for value in values]
    if len(axes) != len(set(axes)):
        raise ProductVariantError(
            "Pick exactly one value per option", 400, code="one_per_axis"
        )
    if set(axes) != product_option_ids:
        raise ProductVariantError(
            "Pick a value for every option", 400,
            code="incomplete_combination",
        )

    return ids


def _combination_taken(product, option_value_ids, *, except_variant_id=None):
    target = frozenset(option_value_ids)
    for variant in product.variants:
        if variant.id == except_variant_id:
            continue
        current = frozenset(
            link.option_value_id for link in variant.values
        )
        if current == target:
            return True
    return False


def add_variant(product, data):
    ids = _validated_option_value_ids(product, data.get("option_value_ids"))

    if _combination_taken(product, ids):
        raise ProductVariantError(
            "A variant for this combination already exists",
            409,
            code="combination_taken",
        )

    variant = ProductVariant(
        product_id=product.id,
        sku=(data.get("sku") or None),
        price=_read_price(data),
        stock=_read_stock(data, required=True),
        is_active=True,
    )
    db.session.add(variant)
    db.session.flush()

    for value_id in ids:
        db.session.add(
            ProductVariantValue(
                variant_id=variant.id, option_value_id=value_id
            )
        )

    db.session.commit()
    return variant


def update_variant(product, variant_id, data):
    """Edit ``sku`` / ``price`` / ``stock``.

    ``stock`` here is a vendor overwriting their own count — a plain
    assignment, not the conditional ``WHERE stock >= :qty`` decrement
    ``order_service._reserve_variant_stock`` uses, because no concurrent
    checkout races a vendor's own edit the way two customers race each other.
    """
    variant = _get_variant(product, variant_id)

    if "sku" in data:
        variant.sku = (data["sku"] or None)
    if "price" in data:
        variant.price = _read_price(data)
    if "stock" in data:
        variant.stock = _read_stock(data, required=False)

    db.session.commit()
    return variant


def set_variant_active(product, variant_id, is_active):
    """Retire or restore a combination. Setting ``is_active`` False is the
    whole operation — a vendor may retire something they still have stock
    of."""
    variant = _get_variant(product, variant_id)
    if not isinstance(is_active, bool):
        raise ProductVariantError("is_active must be true or false")
    variant.is_active = is_active
    db.session.commit()
    return variant


def delete_variant(product, variant_id):
    """Hard-delete — only a variant that has never been ordered. Once an
    ``order_items`` row points at it, ``is_active`` is the only retirement
    path (the denormalised ``variant_label_*`` means history survives, but
    the row must not dangle)."""
    variant = _get_variant(product, variant_id)

    ordered = (
        db.session.query(OrderItem.id)
        .filter(OrderItem.variant_id == variant.id)
        .first()
    )
    if ordered is not None:
        raise ProductVariantError(
            "This variant has been ordered — deactivate it instead.",
            409,
            code="variant_ordered",
        )

    db.session.delete(variant)
    db.session.commit()
