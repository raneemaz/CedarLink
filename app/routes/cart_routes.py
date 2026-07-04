from flask import Blueprint, request, jsonify
from flask_jwt_extended import jwt_required, get_jwt_identity

from app.extensions import db
from app.models.cart import Cart
from app.models.cart_item import CartItem
from app.models.product import Product


cart_bp = Blueprint("cart", __name__)


@cart_bp.route("", methods=["GET"])
@jwt_required()
def get_cart():
    user_id = int(get_jwt_identity())

    cart = Cart.query.filter_by(user_id=user_id).first()

    if not cart:
        return jsonify({
            "stores": [],
            "total": 0
        }), 200

    stores = {}

    for item in cart.items:
        subtotal = float(item.product.price) * item.quantity
        store_id = item.product.store_id

        if store_id not in stores:
            stores[store_id] = {
                "store_id": store_id,
                "items": [],
                "store_subtotal": 0
            }

        stores[store_id]["items"].append({
            "id": item.id,
            "product_id": item.product.id,
            "product_name": item.product.name,
            "price": float(item.product.price),
            "quantity": item.quantity,
            "subtotal": subtotal
        })

        stores[store_id]["store_subtotal"] += subtotal

    store_groups = list(stores.values())

    total = sum(
        store["store_subtotal"]
        for store in store_groups
    )

    return jsonify({
        "cart_id": cart.id,
        "stores": store_groups,
        "total": total
    }), 200


@cart_bp.route("/items", methods=["POST"])
@jwt_required()
def add_to_cart():
    user_id = int(get_jwt_identity())

    data = request.get_json() or {}

    product_id = data.get("product_id")
    quantity = data.get("quantity", 1)

    if not product_id:
        return jsonify({
            "error": "product_id is required"
        }), 400

    if not isinstance(quantity, int) or quantity < 1:
        return jsonify({
            "error": "quantity must be a positive integer"
        }), 400

    product = db.session.get(Product, product_id)

    if not product:
        return jsonify({
            "error": "Product not found"
        }), 404

    cart = Cart.query.filter_by(user_id=user_id).first()

    if not cart:
        cart = Cart(user_id=user_id)
        db.session.add(cart)
        db.session.flush()

    existing_item = CartItem.query.filter_by(
        cart_id=cart.id,
        product_id=product.id
    ).first()

    if existing_item:
        new_quantity = existing_item.quantity + quantity

        if new_quantity > product.stock:
            return jsonify({
                "error": "Requested quantity exceeds available stock",
                "available_stock": product.stock
            }), 400

        existing_item.quantity = new_quantity

    else:
        if quantity > product.stock:
            return jsonify({
                "error": "Requested quantity exceeds available stock",
                "available_stock": product.stock
            }), 400

        new_item = CartItem(
            cart_id=cart.id,
            product_id=product.id,
            quantity=quantity
        )

        db.session.add(new_item)

    db.session.commit()

    return jsonify({
        "message": "Product added to cart"
    }), 200


@cart_bp.route("/items/<int:item_id>", methods=["PUT"])
@jwt_required()
def update_cart_item(item_id):
    user_id = int(get_jwt_identity())

    data = request.get_json() or {}
    quantity = data.get("quantity")

    if not isinstance(quantity, int) or quantity < 1:
        return jsonify({
            "error": "quantity must be a positive integer"
        }), 400

    cart = Cart.query.filter_by(user_id=user_id).first()

    if not cart:
        return jsonify({
            "error": "Cart not found"
        }), 404

    item = CartItem.query.filter_by(
        id=item_id,
        cart_id=cart.id
    ).first()

    if not item:
        return jsonify({
            "error": "Cart item not found"
        }), 404

    if quantity > item.product.stock:
        return jsonify({
            "error": "Requested quantity exceeds available stock",
            "available_stock": item.product.stock
        }), 400

    item.quantity = quantity

    db.session.commit()

    return jsonify({
        "message": "Cart item quantity updated",
        "item_id": item.id,
        "quantity": item.quantity
    }), 200


@cart_bp.route("/items/<int:item_id>", methods=["DELETE"])
@jwt_required()
def delete_cart_item(item_id):
    user_id = int(get_jwt_identity())

    cart = Cart.query.filter_by(user_id=user_id).first()

    if not cart:
        return jsonify({
            "error": "Cart not found"
        }), 404

    item = CartItem.query.filter_by(
        id=item_id,
        cart_id=cart.id
    ).first()

    if not item:
        return jsonify({
            "error": "Cart item not found"
        }), 404

    db.session.delete(item)
    db.session.commit()

    return jsonify({
        "message": "Cart item removed"
    }), 200
