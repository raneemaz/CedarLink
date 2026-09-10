"""Vendor-facing CRUD for a product's options, values and variants (V-2).

Every route: load the product, check the caller owns its store (or is an
admin) — the same gate ``product_routes.update_product`` uses — hand off to
``product_variant_service``, and return the refreshed
``variant_fields(product, include_inactive=True)`` so the vendor UI can
repaint from the response without re-fetching. See
docs/decisions/0036-variant-management-and-picker.md.
"""

from flask import Blueprint, request, jsonify
from flask_jwt_extended import jwt_required, get_jwt, get_jwt_identity

from app.extensions import db
from app.models.product import Product
from app.services import product_variant_service as svc
from app.services.product_variant_service import ProductVariantError
from app.utils.product_payload import variant_fields


product_variant_bp = Blueprint("product_variant_bp", __name__)


def _load_owned_product(product_id):
    product = db.session.get(Product, product_id)
    if product is None or product.deleted_at is not None:
        raise ProductVariantError("Product not found", 404)

    if (
        get_jwt().get("role") != "admin"
        and product.store.owner_id != int(get_jwt_identity())
    ):
        raise ProductVariantError("Not allowed to edit this product", 403)

    return product


def _handle(product_id, action, status=200):
    try:
        product = _load_owned_product(product_id)
        action(product)
    except ProductVariantError as exc:
        return jsonify(exc.payload), exc.status_code

    return jsonify(variant_fields(product, include_inactive=True)), status


def _body():
    return request.get_json() or {}


# --------------------------------------------------------------------------- #
# Options
# --------------------------------------------------------------------------- #

@product_variant_bp.route("/products/<int:id>/options", methods=["POST"])
@jwt_required()
def create_option(id):
    return _handle(id, lambda p: svc.add_option(p, _body()), 201)


@product_variant_bp.route(
    "/products/<int:id>/options/<int:option_id>", methods=["PUT"]
)
@jwt_required()
def update_option(id, option_id):
    return _handle(id, lambda p: svc.update_option(p, option_id, _body()))


@product_variant_bp.route(
    "/products/<int:id>/options/<int:option_id>", methods=["DELETE"]
)
@jwt_required()
def delete_option(id, option_id):
    return _handle(id, lambda p: svc.delete_option(p, option_id))


# --------------------------------------------------------------------------- #
# Option values
# --------------------------------------------------------------------------- #

@product_variant_bp.route(
    "/products/<int:id>/options/<int:option_id>/values", methods=["POST"]
)
@jwt_required()
def create_value(id, option_id):
    return _handle(
        id, lambda p: svc.add_value(p, option_id, _body()), 201
    )


@product_variant_bp.route(
    "/products/<int:id>/options/<int:option_id>/values/<int:value_id>",
    methods=["PUT"],
)
@jwt_required()
def update_value(id, option_id, value_id):
    return _handle(
        id, lambda p: svc.update_value(p, option_id, value_id, _body())
    )


@product_variant_bp.route(
    "/products/<int:id>/options/<int:option_id>/values/<int:value_id>",
    methods=["DELETE"],
)
@jwt_required()
def delete_value(id, option_id, value_id):
    return _handle(
        id, lambda p: svc.delete_value(p, option_id, value_id)
    )


# --------------------------------------------------------------------------- #
# Variants
# --------------------------------------------------------------------------- #

@product_variant_bp.route("/products/<int:id>/variants", methods=["POST"])
@jwt_required()
def create_variant(id):
    return _handle(id, lambda p: svc.add_variant(p, _body()), 201)


@product_variant_bp.route(
    "/products/<int:id>/variants/<int:variant_id>", methods=["PUT"]
)
@jwt_required()
def update_variant(id, variant_id):
    return _handle(
        id, lambda p: svc.update_variant(p, variant_id, _body())
    )


@product_variant_bp.route(
    "/products/<int:id>/variants/<int:variant_id>", methods=["PATCH"]
)
@jwt_required()
def set_variant_active(id, variant_id):
    return _handle(
        id,
        lambda p: svc.set_variant_active(
            p, variant_id, _body().get("is_active")
        ),
    )


@product_variant_bp.route(
    "/products/<int:id>/variants/<int:variant_id>", methods=["DELETE"]
)
@jwt_required()
def delete_variant(id, variant_id):
    return _handle(id, lambda p: svc.delete_variant(p, variant_id))
