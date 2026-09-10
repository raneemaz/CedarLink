"""V-1 — resolving the unit price of a line (ADR 0035).

``order_service.resolve_unit_price`` is the one place a cart/order line's
unit price is decided: the variant's own price when it set one, the
product's price otherwise. Every caller (cart totals, /orders/preview, the
checkout write) goes through it, so a quote and a charge cannot diverge.
"""

from decimal import Decimal

from app.services.order_service import resolve_unit_price


def test_variant_price_overrides_the_product_price(make_product, make_variant):
    product = make_product(price=12.00)
    variant = make_variant(product, price=Decimal("22.00"), stock=3)

    assert resolve_unit_price(product, variant) == Decimal("22.00")


def test_variant_without_a_price_falls_back_to_the_product(
    make_product, make_variant
):
    product = make_product(price=12.00)
    variant = make_variant(product, price=None, stock=3)

    resolved = resolve_unit_price(product, variant)

    assert resolved == product.price
    assert resolved == Decimal("12.00")


def test_a_plain_line_with_no_variant_is_priced_as_before(make_product):
    product = make_product(price=9.50)

    assert resolve_unit_price(product, None) == product.price


def test_resolution_stays_decimal_never_float(make_product, make_variant):
    product = make_product(price=10.00)
    override = make_variant(product, price=Decimal("15.00"), stock=1)
    fallback = make_variant(product, price=None, stock=1)

    assert isinstance(resolve_unit_price(product, override), Decimal)
    assert isinstance(resolve_unit_price(product, fallback), Decimal)
