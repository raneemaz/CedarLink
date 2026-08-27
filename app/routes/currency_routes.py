from flask import Blueprint, jsonify

from app.services.exchange_rate_service import get_rates

currency_bp = Blueprint("currency", __name__, url_prefix="/api")


@currency_bp.route("/exchange-rates", methods=["GET"])
def exchange_rates():
    """Public: display-only conversion rates relative to the base currency.

    These rates are never used for cart, checkout, order or payment amounts.
    """
    return jsonify(get_rates()), 200
