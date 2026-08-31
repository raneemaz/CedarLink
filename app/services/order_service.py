"""Order lifecycle: pricing a cart, checkout, listing, status transitions.

CL-15 — the cart is priced in exactly one place: ``price_cart``. Both
``POST /api/orders/preview`` (quote) and ``POST /api/orders`` (charge) call
it, so the quoted total and the charged total cannot drift apart.

Route handlers parse the request, call one function here, and serialize the
result. Business-rule failures are raised as ``OrderError`` carrying the
exact HTTP status and JSON body the route should return.
"""

from decimal import Decimal

from sqlalchemy import select, update

from app.extensions import db
from app.models.cart import Cart
from app.models.cart_item import CartItem
from app.models.order import Order
from app.models.order_item import OrderItem
from app.models.product import Product
from app.models.store import Store
from app.services.notification_service import (
    notify_order_canceled,
    notify_order_placed,
    notify_order_status_changed,
)

# The only forward moves a vendor may make. A status with no entry here is
# terminal (delivered / canceled).
ORDER_STATUS_TRANSITIONS = {
    "pending": "processing",
    "processing": "delivered",
}


class OrderError(Exception):
    """A checkout / order operation that failed a business rule.

    Carries the HTTP status and the JSON body the route returns verbatim, so
    the one error shape is identical to the pre-refactor handlers.
    """

    def __init__(self, message, status_code=400, **extra):
        super().__init__(message)
        self.status_code = status_code
        self.payload = {"error": message, **extra}


# --------------------------------------------------------------------------- #
# Serialization helpers
# --------------------------------------------------------------------------- #

def _serialize_item(item):
    product = item.product
    return {
        "id": item.id,
        "product_id": item.product_id,
        # English canonical + every translation; the client picks the
        # display language (C.5).
        "product_name": product.name_en,
        "product_name_en": product.name_en,
        "product_name_ar": product.name_ar,
        "product_name_fr": product.name_fr,
        "quantity": item.quantity,
        "unit_price": float(item.unit_price),
        "subtotal": float(item.unit_price * item.quantity),
    }


def _serialize_order(order):
    return {
        "id": order.id,
        "store_id": order.store_id,
        "status": order.status,
        "delivery_address": order.delivery_address,
        "total_price": float(order.total_price),
        "created_at": order.created_at.isoformat(),
        "delivery_city": order.delivery_city,
        "items": [_serialize_item(item) for item in order.items],
    }


def _serialize_status_change(order):
    return {
        "id": order.id,
        "store_id": order.store_id,
        "status": order.status,
        "updated_at": order.updated_at.isoformat(),
    }


# --------------------------------------------------------------------------- #
# Pricing — the single source of truth (CL-15)
# --------------------------------------------------------------------------- #

def price_cart(user_id, delivery_city):
    """Group the user's cart by store and compute subtotals + delivery fees.

    Returns a dict holding the resolved city, the flat cart-item list (for
    the caller that persists), and one entry per store with its ``Store``,
    its cart items, subtotal, delivery fee and total.

    Raises ``OrderError`` — with the legacy status code and body — on an
    empty cart, a vanished or hidden product, insufficient stock, a missing
    store, or a store that has turned off delivery.
    """
    if not delivery_city or not delivery_city.strip():
        raise OrderError("Delivery city is required")

    city = delivery_city.strip()

    cart = Cart.query.filter_by(user_id=user_id).first()

    if not cart:
        raise OrderError("Cart is empty")

    cart_items = CartItem.query.filter_by(cart_id=cart.id).all()

    if not cart_items:
        raise OrderError("Cart is empty")

    items_by_store = {}

    for item in cart_items:
        product = db.session.get(Product, item.product_id)

        if not product:
            raise OrderError(f"Product {item.product_id} not found", 404)

        if product.deleted_at is not None or not product.store.is_visible:
            raise OrderError(
                f"\"{product.name}\" is no longer available. "
                "Remove it from your cart to continue.",
                400,
                product_id=product.id,
                product_name=product.name,
            )

        if product.stock < item.quantity:
            raise OrderError(
                "Insufficient stock",
                400,
                product_id=product.id,
                product_name=product.name,
                available_stock=product.stock,
                requested_quantity=item.quantity,
            )

        items_by_store.setdefault(product.store_id, []).append(
            {"cart_item": item, "product": product}
        )

    stores = []
    subtotal_total = Decimal("0")
    delivery_total = Decimal("0")

    for store_id, grouped_items in items_by_store.items():
        store = db.session.get(Store, store_id)

        if not store:
            raise OrderError(f"Store {store_id} not found", 404)

        if not store.delivery_available:
            raise OrderError(
                "Delivery is not available for this store",
                400,
                store_id=store.id,
                store_name=store.name,
            )

        # Decimal end to end — Product.price is Numeric now (CL-07).
        subtotal = sum(
            (
                entry["product"].price * entry["cart_item"].quantity
                for entry in grouped_items
            ),
            Decimal("0"),
        )

        if city.lower() == store.location.strip().lower():
            delivery_fee = store.inside_city_delivery_fee
        else:
            delivery_fee = store.outside_city_delivery_fee
        delivery_fee = Decimal(delivery_fee or 0)

        stores.append({
            "store": store,
            "store_id": store.id,
            "store_name": store.name,
            "items": grouped_items,
            "subtotal": subtotal,
            "delivery_fee": delivery_fee,
            "total": subtotal + delivery_fee,
        })

        subtotal_total += subtotal
        delivery_total += delivery_fee

    return {
        "delivery_city": city,
        "cart_items": cart_items,
        "stores": stores,
        "subtotal": subtotal_total,
        "delivery_fee": delivery_total,
        "total": subtotal_total + delivery_total,
    }


def serialize_quote(pricing):
    """The ``/orders/preview`` body: pricing without the ORM objects.

    Decimal -> float happens here, at the JSON boundary, and nowhere earlier.
    """
    return {
        "delivery_city": pricing["delivery_city"],
        "subtotal": float(pricing["subtotal"]),
        "delivery_fee": float(pricing["delivery_fee"]),
        "total": float(pricing["total"]),
        "stores": [
            {
                "store_id": group["store_id"],
                "store_name": group["store_name"],
                "subtotal": float(group["subtotal"]),
                "delivery_fee": float(group["delivery_fee"]),
                "total": float(group["total"]),
            }
            for group in pricing["stores"]
        ],
    }


# --------------------------------------------------------------------------- #
# Checkout — prices with the same function, then persists
# --------------------------------------------------------------------------- #

def _reserve_stock(product, quantity):
    """Decrement stock in one conditional statement (CL-06).

    ``UPDATE products SET stock = stock - :qty WHERE id = :id AND stock >= :qty``
    A rowcount of 0 means someone else took the last units between pricing
    and here — raise the same "Insufficient stock" error the pre-check does.
    """
    reserved = db.session.execute(
        update(Product)
        .where(Product.id == product.id, Product.stock >= quantity)
        .values(stock=Product.stock - quantity)
        .execution_options(synchronize_session=False)
    )

    if reserved.rowcount == 0:
        on_hand = db.session.execute(
            select(Product.stock).where(Product.id == product.id)
        ).scalar_one()

        raise OrderError(
            "Insufficient stock",
            400,
            product_id=product.id,
            product_name=product.name,
            available_stock=on_hand,
            requested_quantity=quantity,
        )


def checkout(user_id, delivery_address, delivery_city):
    """Turn the priced cart into one order per store and empty the cart.

    Raises ``OrderError`` for the pricing failures above; lets unexpected
    errors propagate so the route can roll back and return its 500 shape.
    """
    pricing = price_cart(user_id, delivery_city)

    address = delivery_address.strip()
    city = pricing["delivery_city"]

    created = []

    for group in pricing["stores"]:
        order = Order(
            user_id=user_id,
            store_id=group["store_id"],
            status="pending",
            delivery_address=address,
            delivery_city=city,
            total_price=group["total"],
        )

        db.session.add(order)
        db.session.flush()

        for entry in group["items"]:
            _reserve_stock(entry["product"], entry["cart_item"].quantity)

            db.session.add(OrderItem(
                order_id=order.id,
                product_id=entry["product"].id,
                quantity=entry["cart_item"].quantity,
                unit_price=entry["product"].price,
            ))

        created.append({
            "order": order,
            "subtotal": group["subtotal"],
            "delivery_fee": group["delivery_fee"],
        })

    for item in pricing["cart_items"]:
        db.session.delete(item)

    db.session.commit()

    # The business transaction is durable; notifications are best-effort.
    for entry in created:
        notify_order_placed(entry["order"])

    return {
        "message": "Checkout successful",
        "checkout_price": float(
            sum(
                (entry["order"].total_price for entry in created),
                Decimal("0"),
            )
        ),
        "orders": [
            {
                "id": entry["order"].id,
                "store_id": entry["order"].store_id,
                "status": entry["order"].status,
                "subtotal": float(entry["subtotal"]),
                "delivery_city": city,
                "delivery_fee": float(entry["delivery_fee"]),
                "total_price": float(entry["order"].total_price),
            }
            for entry in created
        ],
    }


# --------------------------------------------------------------------------- #
# Reads
# --------------------------------------------------------------------------- #

def list_customer_orders(user_id):
    orders = (
        Order.query.filter_by(user_id=user_id)
        .order_by(Order.created_at.desc())
        .all()
    )
    return [_serialize_order(order) for order in orders]


def get_customer_order(user_id, order_id):
    order = db.session.get(Order, order_id)

    if not order:
        raise OrderError("Order not found", 404)

    if order.user_id != user_id:
        raise OrderError("You are not authorized to view this order", 403)

    detail = _serialize_order(order)
    detail["updated_at"] = order.updated_at.isoformat()
    return detail


def list_vendor_orders(user_id, status_filter=None):
    store = Store.query.filter_by(owner_id=user_id).first()

    if not store:
        raise OrderError("Store not found for this vendor", 404)

    query = Order.query.filter_by(store_id=store.id)

    if status_filter:
        if status_filter not in (
            "pending", "processing", "delivered", "canceled"
        ):
            raise OrderError("Invalid order status")

        query = query.filter_by(status=status_filter)

    orders = query.order_by(Order.created_at.desc()).all()

    result = []

    for order in orders:
        assignment = order.delivery_assignment

        result.append({
            "id": order.id,
            "user_id": order.user_id,
            "customer": {
                "id": order.user.id,
                "first_name": order.user.first_name,
                "last_name": order.user.last_name,
                "email": order.user.email,
                "phone": order.user.phone,
            },
            "store_id": order.store_id,
            "status": order.status,
            "delivery_address": order.delivery_address,
            "delivery_city": order.delivery_city,
            "total_price": float(order.total_price),
            "created_at": order.created_at.isoformat(),
            "delivery_assignment": (
                assignment.to_dict() if assignment else None
            ),
            "items": [_serialize_item(item) for item in order.items],
        })

    return result


# --------------------------------------------------------------------------- #
# Writes
# --------------------------------------------------------------------------- #

def transition_order_status(user_id, order_id, new_status):
    if not new_status:
        raise OrderError("Status is required")

    order = db.session.get(Order, order_id)

    if not order:
        raise OrderError("Order not found", 404)

    store = db.session.get(Store, order.store_id)

    if not store or store.owner_id != user_id:
        raise OrderError(
            "You are not authorized to update this order", 403
        )

    expected_next_status = ORDER_STATUS_TRANSITIONS.get(order.status)

    if expected_next_status is None:
        raise OrderError(
            f"Order with status '{order.status}' cannot be updated"
        )

    if new_status != expected_next_status:
        raise OrderError(
            "Invalid status transition",
            400,
            current_status=order.status,
            allowed_next_status=expected_next_status,
        )

    order.status = new_status
    db.session.commit()

    notify_order_status_changed(order)

    return {
        "message": "Order status updated successfully",
        "order": _serialize_status_change(order),
    }


def cancel_order(user_id, order_id):
    order = db.session.get(Order, order_id)

    if not order:
        raise OrderError("Order not found", 404)

    if order.user_id != user_id:
        raise OrderError(
            "You are not authorized to cancel this order", 403
        )

    if order.status != "pending":
        raise OrderError(
            "Only pending orders can be canceled",
            400,
            current_status=order.status,
        )

    order.status = "canceled"

    for item in order.items:
        product = db.session.get(Product, item.product_id)

        if product:
            product.stock += item.quantity

    db.session.commit()

    notify_order_canceled(order)

    return {
        "message": "Order canceled successfully",
        "order": _serialize_status_change(order),
    }
