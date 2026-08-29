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
        query = query.filter(
            or_(
                Product.name.ilike(f"%{keyword}%"),
                Product.description.ilike(f"%{keyword}%")
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

    # Hide products from deactivated stores on the storefront (CL-12), but
    # not when the store's own vendor is browsing their catalogue.
    if not _owns_store(store_id):
        query = query.join(Store).filter(Store.is_active.is_(True))

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
            "name": product.name,
            "price": product.price,
            "stock": product.stock,
            "description": product.description,
            "store_id": product.store_id,
            "category_id": product.category_id,
            "image": product_image_url(first_image)
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
    product = Product.query.get(id)

    if not product or product.deleted_at is not None:
        return jsonify({
            "message": "Product not found"
        }), 404

    # A product in a deactivated store is hidden from the storefront but
    # still reachable by that store's own vendor (CL-12).
    if not product.store.is_active and not _owns_store(product.store_id):
        return jsonify({
            "message": "Product not found"
        }), 404

    images = [
        {"id": img.id, "url": product_image_url(img.image_url)}
        for img in product.images
    ]

    return jsonify({
        "id": product.id,
        "name": product.name,
        "description": product.description,
        "price": product.price,
        "stock": product.stock,
        "store_id": product.store_id,
        "category_id": product.category_id,
        "images": images,
        "image": images[0]["url"] if images else None
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
        "name",
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

    # Extract values
    name = data.get("name")
    description = data.get("description")
    price = data.get("price")
    stock = data.get("stock")
    store_id = data.get("store_id")
    category_id = data.get("category_id")

    # Validate data types
    if not isinstance(name, str) or not name.strip():
        return jsonify({
            "message": "Product name must be a non-empty string"
        }), 400

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
    category = Category.query.get(category_id)

    if not category:
        return jsonify({
            "message": "Invalid category"
        }), 404

    # Create product
    product = Product(
        name=name.strip(),
        description=description,
        price=price,
        stock=stock,
        store_id=store.id,
        category_id=category.id
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
    product = Product.query.get_or_404(id)

    if claims.get("role") != "admin" and product.store.owner_id != user_id:
        return jsonify({"message": "Not allowed to edit this product"}), 403

    data = request.get_json()

    if "name" in data:
        if not isinstance(data["name"], str) or not data["name"].strip():
            return jsonify({"message": "Name cannot be empty"}), 400
        product.name = data["name"].strip()

    if "description" in data:
        product.description = data["description"]

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

        from app.models.category import Category

        category = Category.query.get(category_id)
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
    product = Product.query.get_or_404(id)

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
