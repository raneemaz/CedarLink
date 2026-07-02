from flask import Blueprint, request, jsonify
from app.extensions import db
from app.models.product import Product
from flask_jwt_extended import jwt_required, get_jwt, get_jwt_identity
from app.models.store import Store

product_bp = Blueprint("product_bp", __name__)


@product_bp.route("/products", methods=["GET"])
def test_products():
    return jsonify({"message": "Product routes working"}), 200


@product_bp.route("/products", methods=["GET"])
def get_products():
    products = Product.query.all()
    result = []
    for p in products:
        result.append({
            "id": p.id,
            "name": p.name,
            "price": p.price,
            "stock": p.stock,
            "store_id": p.store_id,
            "category_id": p.category_id
        })

        return jsonify(result), 200


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
