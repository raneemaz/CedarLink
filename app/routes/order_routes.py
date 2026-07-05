from flask import Blueprint, request, jsonify
from flask_jwt_extended import jwt_required, get_jwt_identity

from app.extensions import db
from app.models.order import Order
from app.models.order_item import OrderItem
from app.models.cart import Cart
from app.models.cart_item import CartItem
from app.models.product import Product
from app.models.store import Store


order_bp = Blueprint("order_bp", __name__)


@order_bp.route("/orders", methods=["POST"])
@jwt_required()
def checkout():
    user_id = int(get_jwt_identity())

    data = request.get_json() or {}
    delivery_address = data.get("delivery_address")

    if not delivery_address or not delivery_address.strip():
        return jsonify({
            "error": "Delivery address is required"
        }), 400

    cart = Cart.query.filter_by(user_id=user_id).first()

    if not cart:
        return jsonify({
            "error": "Cart is empty"
        }), 400

    cart_items = CartItem.query.filter_by(cart_id=cart.id).all()

    if not cart_items:
        return jsonify({
            "error": "Cart is empty"
        }), 400

    items_by_store = {}

    for item in cart_items:
        product = db.session.get(Product, item.product_id)

        if not product:
            return jsonify({
                "error": f"Product {item.product_id} not found"
            }), 404

        if product.stock < item.quantity:
            return jsonify({
                "error": "Insufficient stock",
                "product_id": product.id,
                "product_name": product.name,
                "available_stock": product.stock,
                "requested_quantity": item.quantity
            }), 400

        if product.store_id not in items_by_store:
            items_by_store[product.store_id] = []

        items_by_store[product.store_id].append({
            "cart_item": item,
            "product": product
        })

    try:
        created_orders = []

        for store_id, grouped_items in items_by_store.items():

            total_price = sum(
                item_data["product"].price
                * item_data["cart_item"].quantity
                for item_data in grouped_items
            )

            order = Order(
                user_id=user_id,
                store_id=store_id,
                status="pending",
                delivery_address=delivery_address.strip(),
                total_price=total_price
            )

            db.session.add(order)

            db.session.flush()

            for item_data in grouped_items:
                cart_item = item_data["cart_item"]
                product = item_data["product"]

                order_item = OrderItem(
                    order_id=order.id,
                    product_id=product.id,
                    quantity=cart_item.quantity,
                    unit_price=product.price
                )

                db.session.add(order_item)

                product.stock -= cart_item.quantity

            created_orders.append(order)

        for item in cart_items:
            db.session.delete(item)

        db.session.commit()

        return jsonify({
            "message": "Checkout successful",
            "orders": [
                {
                    "id": order.id,
                    "store_id": order.store_id,
                    "status": order.status,
                    "total_price": float(order.total_price)
                }
                for order in created_orders
            ]
        }), 201

    except Exception:
        db.session.rollback()

        return jsonify({
            "error": "Checkout failed"
        }), 500


@order_bp.route("/orders", methods=["GET"])
@jwt_required()
def get_orders():
    user_id = int(get_jwt_identity())

    orders = Order.query.filter_by(
        user_id=user_id
    ).order_by(
        Order.created_at.desc()
    ).all()

    result = []

    for order in orders:
        order_data = {
            "id": order.id,
            "store_id": order.store_id,
            "status": order.status,
            "delivery_address": order.delivery_address,
            "total_price": float(order.total_price),
            "created_at": order.created_at.isoformat(),
            "items": []
        }

        for item in order.items:
            order_data["items"].append({
                "id": item.id,
                "product_id": item.product_id,
                "product_name": item.product.name,
                "quantity": item.quantity,
                "unit_price": float(item.unit_price),
                "subtotal": float(item.unit_price * item.quantity)
            })

        result.append(order_data)

    return jsonify({
        "orders": result
    }), 200


@order_bp.route("/orders/<int:id>", methods=["GET"])
@jwt_required()
def get_order(id):
    user_id = int(get_jwt_identity())

    order = db.session.get(Order, id)

    if not order:
        return jsonify({
            "error": "Order not found"
        }), 404

    if order.user_id != user_id:
        return jsonify({
            "error": "You are not authorized to view this order"
        }), 403

    items = []

    for item in order.items:
        items.append({
            "id": item.id,
            "product_id": item.product_id,
            "product_name": item.product.name,
            "quantity": item.quantity,
            "unit_price": float(item.unit_price),
            "subtotal": float(item.unit_price * item.quantity)
        })

    return jsonify({
        "order": {
            "id": order.id,
            "store_id": order.store_id,
            "status": order.status,
            "delivery_address": order.delivery_address,
            "total_price": float(order.total_price),
            "created_at": order.created_at.isoformat(),
            "updated_at": order.updated_at.isoformat(),
            "items": items
        }
    }), 200


@order_bp.route("/vendor/orders", methods=["GET"])
@jwt_required()
def get_vendor_orders():
    user_id = int(get_jwt_identity())

    store = Store.query.filter_by(owner_id=user_id).first()

    if not store:
        return jsonify({
            "error": "Store not found for this vendor"
        }), 404

    status_filter = request.args.get("status")

    query = Order.query.filter_by(store_id=store.id)

    if status_filter:
        allowed_statuses = [
            "pending",
            "processing",
            "delivered",
            "canceled"
        ]

        if status_filter not in allowed_statuses:
            return jsonify({
                "error": "Invalid order status"
            }), 400

        query = query.filter_by(status=status_filter)

    orders = query.order_by(
        Order.created_at.desc()
    ).all()

    result = []

    for order in orders:
        order_data = {
            "id": order.id,
            "user_id": order.user_id,
            "store_id": order.store_id,
            "status": order.status,
            "delivery_address": order.delivery_address,
            "total_price": float(order.total_price),
            "created_at": order.created_at.isoformat(),
            "items": []
        }

        for item in order.items:
            order_data["items"].append({
                "id": item.id,
                "product_id": item.product_id,
                "product_name": item.product.name,
                "quantity": item.quantity,
                "unit_price": float(item.unit_price),
                "subtotal": float(
                    item.unit_price * item.quantity
                )
            })

        result.append(order_data)

    return jsonify({
        "orders": result
    }), 200


@order_bp.route("/orders/<int:id>/status", methods=["PATCH"])
@jwt_required()
def update_order_status(id):
    user_id = int(get_jwt_identity())

    data = request.get_json() or {}
    new_status = data.get("status")

    if not new_status:
        return jsonify({
            "error": "Status is required"
        }), 400

    store = Store.query.filter_by(owner_id=user_id).first()

    if not store:
        return jsonify({
            "error": "Store not found for this vendor"
        }), 404

    order = db.session.get(Order, id)

    if not order:
        return jsonify({
            "error": "Order not found"
        }), 404

    if order.store_id != store.id:
        return jsonify({
            "error": "You are not authorized to update this order"
        }), 403

    allowed_transitions = {
        "pending": "processing",
        "processing": "delivered"
    }

    expected_next_status = allowed_transitions.get(order.status)

    if expected_next_status is None:
        return jsonify({
            "error": f"Order with status '{order.status}' cannot be updated"
        }), 400

    if new_status != expected_next_status:
        return jsonify({
            "error": "Invalid status transition",
            "current_status": order.status,
            "allowed_next_status": expected_next_status
        }), 400

    try:
        order.status = new_status
        db.session.commit()

        return jsonify({
            "message": "Order status updated successfully",
            "order": {
                "id": order.id,
                "store_id": order.store_id,
                "status": order.status,
                "updated_at": order.updated_at.isoformat()
            }
        }), 200

    except Exception:
        db.session.rollback()

        return jsonify({
            "error": "Failed to update order status"
        }), 500


@order_bp.route("/orders/<int:id>/cancel", methods=["PATCH"])
@jwt_required()
def cancel_order(id):
    user_id = int(get_jwt_identity())

    order = db.session.get(Order, id)

    if not order:
        return jsonify({
            "error": "Order not found"
        }), 404

    if order.user_id != user_id:
        return jsonify({
            "error": "You are not authorized to cancel this order"
        }), 403

    if order.status != "pending":
        return jsonify({
            "error": "Only pending orders can be canceled",
            "current_status": order.status
        }), 400

    try:
        order.status = "canceled"

        for item in order.items:
            product = db.session.get(Product, item.product_id)

            if product:
                product.stock += item.quantity

        db.session.commit()

        return jsonify({
            "message": "Order canceled successfully",
            "order": {
                "id": order.id,
                "store_id": order.store_id,
                "status": order.status,
                "updated_at": order.updated_at.isoformat()
            }
        }), 200

    except Exception:
        db.session.rollback()

        return jsonify({
            "error": "Failed to cancel order"
        }), 500
