from flask import Blueprint, request, jsonify
from flask_jwt_extended import jwt_required, get_jwt_identity

from app.extensions import db
from app.models.cart import Cart
from app.models.cart_item import CartItem
from app.models.product import Product
from app.services import coupon_service, order_service, store_service
from app.services.coupon_service import CouponError
from app.services.order_service import OrderError


cart_bp = Blueprint("cart", __name__)


@cart_bp.route("", methods=["GET"])
@jwt_required()
def get_cart():
    user_id = int(get_jwt_identity())

    cart = Cart.query.filter_by(user_id=user_id).first()

    if not cart:
        return jsonify({
            "stores": [],
            "total": 0,
            "coupon_code": None,
            "discount": 0,
        }), 200

    stores = {}

    for item in cart.items:
        subtotal = float(item.product.price) * item.quantity
        store_id = item.product.store_id

        if store_id not in stores:
            store_obj = item.product.store
            open_now, reason = store_service.is_open_now(store_obj)

            # The cart has to tell "closed, we will deliver later" from
            # "closed, you cannot order" — the old warning implied the
            # second for both. See ADR 0025.
            takes_orders = open_now or (
                reason == store_service.CLOSED_OUTSIDE_HOURS
                and store_obj.accepts_orders_when_closed
            )
            opens_at = (
                store_service.next_opening_time(store_obj)
                if not open_now and takes_orders
                else None
            )

            stores[store_id] = {
                "store_id": store_id,
                "store_name": store_obj.name,
                "is_open_now": open_now,
                "accepts_orders": takes_orders,
                "next_opening_time": (
                    opens_at.isoformat() if opens_at else None
                ),
                "items": [],
                "store_subtotal": 0
            }

        stores[store_id]["items"].append({
            "id": item.id,
            "product_id": item.product.id,
            # English canonical + every translation; the client picks the
            # display language (C.5).
            "product_name": item.product.name_en,
            "product_name_en": item.product.name_en,
            "product_name_ar": item.product.name_ar,
            "product_name_fr": item.product.name_fr,
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

    # Goods only — the cart has no delivery city, so no fees. Computed by
    # the same function checkout uses, so the cart cannot quote a discount
    # the order would not honour.
    coupon_code, discount = order_service.cart_discount(cart, user_id)

    return jsonify({
        "cart_id": cart.id,
        "stores": store_groups,
        "total": total,
        "coupon_code": coupon_code,
        "discount": float(discount),
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

    if (
        not product
        or product.deleted_at is not None
        or not product.store.is_visible
    ):
        return jsonify({
            "error": "Product not found"
        }), 404

    # A closed store cannot take new cart items (enforced in the service so
    # cart-add and checkout share one rule).
    try:
        order_service.assert_store_accepts_orders(product.store)
    except OrderError as exc:
        return jsonify(exc.payload), exc.status_code

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


# --------------------------------------------------------------------------- #
# Coupon — validate and hold, never redeem
# --------------------------------------------------------------------------- #

@cart_bp.route("/coupon", methods=["POST"])
@jwt_required()
def apply_coupon():
    """Validate a code against the current cart and quote it.

    Redeems nothing: a preview must never consume a use. On success the
    code is held on the cart so it survives a reload, and the body is the
    same quote shape ``/orders/preview`` returns, discount included.

    On failure the body carries the specific ``code`` — expired, below
    minimum, wrong store — so the interface can say why rather than
    "invalid coupon".
    """
    user_id = int(get_jwt_identity())
    data = request.get_json() or {}

    code = coupon_service.normalize_code(data.get("code"))

    if not code:
        return jsonify({"error": "A coupon code is required"}), 400

    cart = Cart.query.filter_by(user_id=user_id).first()

    if not cart:
        return jsonify({"error": "Cart is empty"}), 400

    # Validated against the goods, which is all a discount ever touches —
    # so the cart can apply a code without knowing where it is going. The
    # checkout page re-prices with its own city and gets the fees.
    try:
        applied, discount, goods = order_service.price_cart_goods(
            cart, user_id, code
        )
    except OrderError as exc:
        return jsonify(exc.payload), exc.status_code
    except CouponError as exc:
        return jsonify(exc.payload), exc.status_code

    cart.coupon_code = code
    db.session.commit()

    return jsonify({
        "coupon_code": applied,
        "discount": float(discount),
        "subtotal": float(goods),
        "total": float(goods - discount),
    }), 200


@cart_bp.route("/coupon", methods=["DELETE"])
@jwt_required()
def clear_coupon():
    """Drop the held code. Idempotent — no cart, or none applied, is fine."""
    user_id = int(get_jwt_identity())

    cart = Cart.query.filter_by(user_id=user_id).first()

    if cart is not None and cart.coupon_code is not None:
        cart.coupon_code = None
        db.session.commit()

    return jsonify({"message": "Coupon removed", "coupon_code": None}), 200
