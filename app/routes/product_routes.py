from datetime import datetime, timezone

from flask import Blueprint, request, jsonify
from app.extensions import db
from app.models.product import Product
from flask_jwt_extended import jwt_required, get_jwt, get_jwt_identity
from app.models.store import Store
from sqlalchemy import or_
from app.models.category import Category
from app.utils.file_utils import product_image_url


product_bp = Blueprint("product_bp", __name__)

# The three interface languages. The API returns every translation and the
# client picks — locale is never negotiated server-side (C.5). See
# docs/decisions/0012-product-category-translation.md.
_LANGUAGES = ("en", "ar", "fr")


def _translation_fields(product):
    """name_en/ar/fr + description_en/ar/fr, plus `name` / `description`
    as English-canonical aliases for any consumer that is not yet
    language-aware."""
    fields = {
        f"{base}_{lang}": getattr(product, f"{base}_{lang}")
        for base in ("name", "description")
        for lang in _LANGUAGES
    }
    fields["name"] = product.name_en
    fields["description"] = product.description_en
    return fields


def _rating_fields(entity):
    """``rating_avg`` (float or None) + ``rating_count`` for a product/store."""
    return {
        "rating_avg": (
            float(entity.rating_avg)
            if entity.rating_avg is not None
            else None
        ),
        "rating_count": entity.rating_count or 0,
    }


def _read_translations(data, *, require_name):
    """Pull translation columns out of a request body.

    English is required on create; on update only the keys present are
    touched. `name` / `description` are accepted as aliases for the `_en`
    key so existing callers keep working.
    """
    values = {}
    errors = []

    def take(base, lang, aliases=()):
        for key in (f"{base}_{lang}", *aliases):
            if key in data:
                return True, data[key]
        return False, None

    for base in ("name", "description"):
        for lang in _LANGUAGES:
            aliases = (base,) if lang == "en" else ()
            present, raw = take(base, lang, aliases)
            if not present:
                continue
            if raw is None or (isinstance(raw, str) and not raw.strip()):
                # Blank clears an optional translation; English cannot be blank.
                if base == "name" and lang == "en":
                    errors.append("Product name (English) cannot be empty")
                    continue
                values[f"{base}_{lang}"] = None
            elif isinstance(raw, str):
                values[f"{base}_{lang}"] = raw.strip()
            else:
                errors.append(f"{base}_{lang} must be a string")

    if require_name and "name_en" not in values:
        errors.append("Product name (English) is required")

    return values, errors


def _owns_store(store_id):
    """True when the current request is the store's own vendor (or an admin).

    Used to let the vendor console keep listing its products while the store
    is deactivated, without exposing those products to the storefront.
    """
    identity = get_jwt_identity()

    if identity is None or store_id is None:
        return False

    store = db.session.get(Store, store_id)

    if store is None:
        return False

    return get_jwt().get("role") == "admin" or store.owner_id == int(identity)


@product_bp.route("/products", methods=["GET"])
@jwt_required(optional=True)
def get_products():
    # Soft-deleted products are gone from the storefront and the vendor list.
    query = Product.query.filter(Product.deleted_at.is_(None))

    sort = request.args.get("sort")
    keyword = request.args.get("keyword")

    def parse_query_param(name, cast, message):
        value = request.args.get(name)

        if value is None:
            return None

        try:
            return cast(value)
        except (TypeError, ValueError):
            raise ValueError(message)

    try:
        category_id = parse_query_param(
            "category_id",
            int,
            "category_id must be an integer"
        )

        store_id = parse_query_param(
            "store_id",
            int,
            "store_id must be an integer"
        )

        min_price = parse_query_param(
            "min_price",
            float,
            "min_price must be a number"
        )

        max_price = parse_query_param(
            "max_price",
            float,
            "max_price must be a number"
        )

        page = parse_query_param(
            "page",
            int,
            "page must be an integer"
        ) or 1

        per_page = parse_query_param(
            "limit",
            int,
            "limit must be an integer"
        ) or 10

    except ValueError as e:
        return jsonify({
            "message": str(e)
        }), 400

    if page < 1:
        return jsonify({
            "message": "page must be greater than 0"
        }), 400

    if per_page < 1:
        return jsonify({
            "message": "limit must be greater than 0"
        }), 400

    if keyword:
        # Match any language column: a customer searching in Arabic must find
        # a product whose Arabic name matches, whatever the interface
        # language. This is substring ILIKE — no diacritic folding or
        # stemming; the Postgres full-text path is documented as future work
        # in docs/decisions/0012-product-category-translation.md.
        like = f"%{keyword}%"
        query = query.filter(
            or_(
                Product.name_en.ilike(like),
                Product.name_ar.ilike(like),
                Product.name_fr.ilike(like),
                Product.description_en.ilike(like),
                Product.description_ar.ilike(like),
                Product.description_fr.ilike(like),
            )
        )

    if request.args.get("in_stock", "").lower() == "true":
        query = query.filter(Product.stock > 0)
    if min_price is not None and max_price is not None:
        if min_price > max_price:
            return jsonify({
                "message": "min_price cannot be greater than max_price"
            }), 400

    if category_id is not None:
        query = query.filter(Product.category_id == category_id)

    if store_id is not None:
        query = query.filter(Product.store_id == store_id)

    # A store removed by an admin (CL-24) is hidden from everyone. A store
    # that is merely deactivated (CL-12) or not yet approved is hidden from
    # the storefront but still visible to its own vendor.
    query = query.join(Store).filter(Store.deleted_at.is_(None))
    if not _owns_store(store_id):
        query = query.filter(Store.is_visible)

    if min_price is not None:
        query = query.filter(Product.price >= min_price)

    if max_price is not None:
        query = query.filter(Product.price <= max_price)

    if sort == "price_asc":
        query = query.order_by(Product.price.asc())
    elif sort == "price_desc":
        query = query.order_by(Product.price.desc())
    elif sort == "newest":
        query = query.order_by(Product.created_at.desc())
    else:
        query = query.order_by(Product.id.desc())

    products = query.paginate(
        page=page,
        per_page=per_page,
        error_out=False
    )

    result = []

    for product in products.items:
        first_image = (
            product.images[0].image_url
            if product.images
            else None
        )

        result.append({
            "id": product.id,
            "price": float(product.price),
            "stock": product.stock,
            "store_id": product.store_id,
            "store_name": product.store.name,
            "category_id": product.category_id,
            "image": product_image_url(first_image),
            **_translation_fields(product),
            **_rating_fields(product),
        })

    return jsonify({
        "products": result,
        "page": products.page,
        "pages": max(products.pages, 1),
        "total": products.total
    }), 200


@product_bp.route("/products/<int:id>", methods=["GET"])
@jwt_required(optional=True)
def get_product(id):
    product = db.session.get(Product, id)

    if not product or product.deleted_at is not None:
        return jsonify({
            "message": "Product not found"
        }), 404

    # A removed store's products are hidden from everyone (CL-24). Products
    # of a deactivated or unapproved store stay reachable by its own vendor.
    store = product.store
    if store.deleted_at is not None or (
        not _owns_store(product.store_id) and not store.is_visible
    ):
        return jsonify({
            "message": "Product not found"
        }), 404

    images = [
        {"id": img.id, "url": product_image_url(img.image_url)}
        for img in product.images
    ]

    return jsonify({
        "id": product.id,
        "price": float(product.price),
        "stock": product.stock,
        "store_id": product.store_id,
        "store_name": product.store.name,
        "category_id": product.category_id,
        "images": images,
        "image": images[0]["url"] if images else None,
        **_translation_fields(product),
        **_rating_fields(product),
    }), 200


@product_bp.route("/products", methods=["POST"])
@jwt_required()
def create_product():
    user_id = get_jwt_identity()
    claims = get_jwt()

    # Only vendors can create products
    if claims.get("role") != "vendor":
        return jsonify({
            "message": "Only vendors can create products"
        }), 403

    # Get request body
    data = request.get_json() or {}

    if not data:
        return jsonify({
            "message": "Request body is required"
        }), 400

    # Required fields
    required_fields = [
        "price",
        "stock",
        "store_id",
        "category_id"
    ]

    missing_fields = [
        field for field in required_fields
        if data.get(field) is None
    ]

    if missing_fields:
        return jsonify({
            "message": "Missing required fields",
            "missing_fields": missing_fields
        }), 400

    # name_en/ar/fr + description_en/ar/fr (English required, rest optional).
    translations, translation_errors = _read_translations(
        data, require_name=True
    )
    if translation_errors:
        return jsonify({"message": translation_errors[0]}), 400

    # Extract values
    price = data.get("price")
    stock = data.get("stock")
    store_id = data.get("store_id")
    category_id = data.get("category_id")

    # Validate data types
    if not isinstance(price, (int, float)):
        return jsonify({
            "message": "Price must be a number"
        }), 400

    if not isinstance(stock, int):
        return jsonify({
            "message": "Stock must be an integer"
        }), 400

    if not isinstance(store_id, int):
        return jsonify({
            "message": "Store ID must be an integer"
        }), 400

    if not isinstance(category_id, int):
        return jsonify({
            "message": "Category ID must be an integer"
        }), 400

    # Validate values
    if price < 0:
        return jsonify({
            "message": "Price cannot be negative"
        }), 400

    if stock < 0:
        return jsonify({
            "message": "Stock cannot be negative"
        }), 400

    # Validate store ownership
    store = Store.query.filter_by(
        id=store_id,
        owner_id=user_id
    ).first()

    if not store:
        return jsonify({
            "message": "Invalid store or not your store"
        }), 403

    # Validate category exists
    category = db.session.get(Category, category_id)

    if not category:
        return jsonify({
            "message": "Invalid category"
        }), 404

    # Create product
    product = Product(
        price=price,
        stock=stock,
        store_id=store.id,
        category_id=category.id,
        **translations,
    )

    db.session.add(product)
    db.session.commit()

    return jsonify({
        "message": "Product created successfully",
        "id": product.id
    }), 201


@product_bp.route("/products/<int:id>", methods=["PUT"])
@jwt_required()
def update_product(id):
    claims = get_jwt()
    user_id = int(get_jwt_identity())
    product = db.session.get(Product, id)

    if not product:
        return jsonify({"message": "Product not found"}), 404

    if claims.get("role") != "admin" and product.store.owner_id != user_id:
        return jsonify({"message": "Not allowed to edit this product"}), 403

    data = request.get_json()

    # name_en/ar/fr + description_en/ar/fr — only the keys present are
    # touched; a blank value clears an optional translation.
    translations, translation_errors = _read_translations(
        data, require_name=False
    )
    if translation_errors:
        return jsonify({"message": translation_errors[0]}), 400
    for column, value in translations.items():
        setattr(product, column, value)

    if "price" in data:
        try:
            price = float(data["price"])
        except (TypeError, ValueError):
            return jsonify({"message": "Price must be a number"}), 400

        if price < 0:
            return jsonify({"message": "Price cannot be negative"}), 400

        product.price = price

    if "stock" in data:
        try:
            stock = int(data["stock"])
        except (TypeError, ValueError):
            return jsonify({"message": "Stock must be an integer"}), 400

        if stock < 0:
            return jsonify({"message": "Stock cannot be negative"}), 400

        product.stock = stock

    if "category_id" in data:
        try:
            category_id = int(data["category_id"])
        except (TypeError, ValueError):
            return jsonify({"message": "Category ID must be an integer"}), 400

        category = db.session.get(Category, category_id)
        if not category:
            return jsonify({"message": "Invalid category"}), 404

        product.category_id = category_id

    db.session.commit()

    return jsonify({
        "message": "Product updated successfully"
    }), 200


@product_bp.route("/products/<int:id>", methods=["DELETE"])
@jwt_required()
def delete_product(id):
    claims = get_jwt()
    user_id = int(get_jwt_identity())
    product = db.session.get(Product, id)

    if not product:
        return jsonify({"message": "Product not found"}), 404

    if claims.get("role") != "admin" and product.store.owner_id != user_id:
        return jsonify({
            "message": "Not allowed to delete this product"
        }), 403

    if product.deleted_at is not None:
        return jsonify({
            "message": "Product not found"
        }), 404

    # Soft delete — the row stays so past orders keep their line items.
    product.deleted_at = datetime.now(timezone.utc)
    db.session.commit()

    return jsonify({
        "message": "Product deleted successfully"
    }), 200
