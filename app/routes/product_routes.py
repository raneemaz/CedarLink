from flask import Blueprint, request, jsonify
from app.extensions import db
from app.models.product import Product
from flask_jwt_extended import jwt_required, get_jwt, get_jwt_identity
from app.models.store import Store
from sqlalchemy import or_


product_bp = Blueprint("product_bp", __name__)


@product_bp.route("/products", methods=["GET"])
def get_products():
    query = Product.query
    sort = request.args.get("sort")
    keyword = request.args.get("keyword")
    category_id = request.args.get("category_id", type=int)
    store_id = request.args.get("store_id", type=int)
    min_price = request.args.get("min_price", type=float)
    max_price = request.args.get("max_price", type=float)
    page = request.args.get("page", 1, type=int)
    per_page = request.args.get("limit", 10, type=int)

    if keyword:
        query = query.filter(
            or_(
                Product.name.ilike(f"%{keyword}%"),
                Product.description.ilike(f"%{keyword}%")
            )
        )
    if category_id:
        query = query.filter(Product.category_id == category_id)
    if store_id:
        query = query.filter(Product.store_id == store_id)
    if min_price is not None:
        query = query.filter(Product.price >= min_price)
    if max_price is not None:
        query = query.filter(Product.price <= max_price)

    if sort == "price_asc":
        query = query.order_by(Product.price.asc())
    if sort == "price_desc":
        query = query.order_by(Product.price.desc())
    if sort == "newest":
        query = query.order_by(Product.created_at.desc())
    else:
        query = query.order_by(Product.id.desc())
    
    products = query.paginate(
        page=page,
        per_page=per_page,
        error_out=False
    )
    result = []

    for p in products.items:
        first_image = p.images[0].image_url if p.images else None
        result.append({
            "id": p.id,
            "name": p.name,
            "price": p.price,
            "stock": p.stock,
            "description": p.description,
            "store_id": p.store_id,
            "category_id": p.category_id,
            "image": first_image
        })

    return jsonify({
        "products": result,
        "page": products.page,
        "pages": products.pages,
        "total": products.total
    }), 200


@product_bp.route("/products/<int:id>", methods=["GET"])
def get_product(id):
    product = Product.query.get_or_404(id)

    return jsonify({
        "id": product.id,
        "name": product.name,
        "description": product.description,
        "price": product.price,
        "stock": product.stock,
        "store_id": product.store_id,
        "category_id": product.category_id
    }), 200


@product_bp.route("/products", methods=["POST"])
@jwt_required()
def create_product():
    user_id = get_jwt_identity()
    claims = get_jwt()
    if claims.get("role") != "vendor":
        return jsonify({"message": "Only vendors can create products"}), 403

    data = request.get_json()

    name = data.get("name")
    price = data.get("price")
    stock = data.get("stock")
    store_id = data.get("store_id")
    category_id = data.get("category_id")

    store = Store.query.filter_by(id=store_id, owner_id=user_id).first()
    if not store:
        return jsonify({"message": "Invalid store or not your store"}), 403

    product = Product(
        name=name,
        description=data.get("description"),
        price=price,
        stock=stock,
        store_id=store.id,
        category_id=category_id
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
    user_id = get_jwt_identity()
    product = Product.query.get_or_404(id)

    if claims.get("role") != "admin" and product.store.owner_id != user_id:
        return jsonify({"message": "Not allowed to edit this product"}), 403

    data = request.get_json()

    product.name = data.get("name", product.name)
    product.description = data.get("description", product.description)
    product.price = data.get("price", product.price)
    product.stock = data.get("stock", product.stock)
    product.category_id = data.get("category_id", product.category_id)

    db.session.commit()

    return jsonify({
        "message": "Product updated successfully"
    }), 200


@product_bp.route("/products/<int:id>", methods=["DELETE"])
@jwt_required()
def delete_product(id):
    claims = get_jwt()
    user_id = get_jwt_identity()
    product = Product.query.get_or_404(id)

    if claims.get("role") != "admin" and product.store.owner_id != user_id:
        return jsonify({"message": "Not allowed to delete this product"}), 403

    db.session.delete(product)
    db.session.commit()

    return jsonify({
        "message": "Product deleted successfully"
    }), 200
