"""Notification preferences + persistent in-app notifications.

``should_notify`` is the preference gate. ``create_notification`` is the single
entry point for persisting an in-app notification; it consults ``should_notify``
so callers never duplicate preference logic. The ``notify_*`` wrappers are the
event-specific helpers routes call, always AFTER their own business commit, via
``_emit`` which isolates any failure from the caller.
"""

from datetime import datetime

from flask import current_app

from app.extensions import db
from app.models.notification import Notification
from app.models.notification_preferences import NotificationPreferences

# Category toggles ("what to notify me about")
CATEGORIES = {"order_updates", "promotions"}

# Channel toggles ("how to reach me")
CHANNELS = {"email", "in_app"}

PREFERENCE_KEYS = CATEGORIES | CHANNELS


def get_or_create_preferences(user_id):
    """Return the user's preferences row, creating a default one if missing."""
    prefs = NotificationPreferences.query.filter_by(user_id=user_id).first()

    if prefs is None:
        prefs = NotificationPreferences(user_id=user_id)
        db.session.add(prefs)
        db.session.commit()

    return prefs


def serialize_preferences(prefs):
    return {
        "order_updates": prefs.order_updates,
        "promotions": prefs.promotions,
        "email": prefs.email,
        "in_app": prefs.in_app,
    }


def apply_preference_updates(prefs, data):
    """Apply only the provided, valid boolean keys.

    Returns ``(ok, error_message)``. Does not commit.
    """
    if not isinstance(data, dict):
        return False, "Request body must be a JSON object"

    unknown = set(data) - PREFERENCE_KEYS

    if unknown:
        return (
            False,
            "Unknown preference keys: " + ", ".join(sorted(unknown)),
        )

    for key in PREFERENCE_KEYS:
        if key in data:
            if not isinstance(data[key], bool):
                return False, f"'{key}' must be true or false"

            setattr(prefs, key, data[key])

    prefs.updated_at = datetime.utcnow()

    return True, None


def should_notify(user_id, category, channel):
    """Preference gate.

    A notification of ``category`` on ``channel`` is allowed only when both the
    category and the channel are enabled for the user.
    """
    if category not in CATEGORIES or channel not in CHANNELS:
        return False

    prefs = get_or_create_preferences(user_id)

    return bool(getattr(prefs, category) and getattr(prefs, channel))


# ---------------------------------------------------------------------------
# Persistent in-app notifications
# ---------------------------------------------------------------------------


def create_notification(
    user_id,
    *,
    category,
    notification_type,
    title,
    message,
    link=None,
    channel="in_app",
):
    """Create a persistent notification IF the user's preferences allow it.

    Adds the row to the session but does NOT commit. Returns the
    ``Notification`` instance, or ``None`` when the preference gate blocks it.
    """
    if category not in CATEGORIES or channel not in CHANNELS:
        return None

    if not should_notify(user_id, category, channel):
        return None

    notification = Notification(
        user_id=user_id,
        category=category,
        type=notification_type,
        title=title,
        message=message,
        link=link,
    )
    db.session.add(notification)

    return notification


def _emit(user_id, *, notification_type, title, message, link=None):
    """Best-effort in-app notification creation, isolated from the caller.

    MUST be called AFTER the business transaction has been committed. Never
    raises: any failure is logged and the notification is rolled back without
    touching the already-committed business change.
    """
    try:
        notification = create_notification(
            user_id,
            category="order_updates",
            notification_type=notification_type,
            title=title,
            message=message,
            link=link,
        )

        if notification is not None:
            db.session.commit()

        return notification
    except Exception:
        db.session.rollback()
        current_app.logger.exception(
            "Failed to create notification (%s) for user %s",
            notification_type,
            user_id,
        )
        return None


def _order_link(order):
    return f"/orders/{order.id}"


def notify_order_placed(order):
    _emit(
        order.user_id,
        notification_type="order_placed",
        title=f"Order #{order.id} placed",
        message="We've received your order and it's now pending.",
        link=_order_link(order),
    )


def notify_order_status_changed(order):
    """Vendor-driven order status change (processing / delivered)."""
    phrases = {
        "processing": "is now being prepared",
        "delivered": "has been marked delivered",
        "canceled": "has been canceled",
    }
    phrase = phrases.get(order.status, f"is now {order.status}")

    _emit(
        order.user_id,
        notification_type="order_status_changed",
        title=f"Order #{order.id} status update",
        message=f"Your order {phrase}.",
        link=_order_link(order),
    )


def notify_order_canceled(order):
    _emit(
        order.user_id,
        notification_type="order_canceled",
        title=f"Order #{order.id} canceled",
        message="Your order has been canceled.",
        link=_order_link(order),
    )


def notify_payment_completed(order):
    """Payment provider confirmed the charge (frames the payment, not status)."""
    _emit(
        order.user_id,
        notification_type="payment_completed",
        title=f"Payment received for order #{order.id}",
        message="Your payment was confirmed. Your order is being processed.",
        link=_order_link(order),
    )


def notify_payment_refunded(order):
    _emit(
        order.user_id,
        notification_type="payment_refunded",
        title=f"Order #{order.id} refunded",
        message="Your payment was refunded and the order was canceled.",
        link=_order_link(order),
    )


def notify_store_announcement(announcement):
    """Best-effort ``promotions`` notification to a store's past customers.

    Call AFTER the announcement is committed. Never raises: a failure is
    logged and rolled back without touching the committed announcement. The
    per-user ``promotions`` preference gate still applies (via
    ``create_notification``).
    """
    from app.models.order import Order

    if not announcement.is_active:
        return

    try:
        user_ids = [
            row[0]
            for row in db.session.query(Order.user_id)
            .filter(Order.store_id == announcement.store_id)
            .distinct()
        ]

        emitted = 0
        for user_id in user_ids:
            notification = create_notification(
                user_id,
                category="promotions",
                notification_type="store_announcement",
                title=announcement.title,
                message=_clip(announcement.body, 500),
                link=f"/stores/{announcement.store_id}",
            )
            if notification is not None:
                emitted += 1

        if emitted:
            db.session.commit()

        return emitted
    except Exception:
        db.session.rollback()
        current_app.logger.exception(
            "Failed to emit announcement notifications for store %s",
            announcement.store_id,
        )
        return 0


def _clip(text, limit):
    text = text or ""
    return text if len(text) <= limit else text[: limit - 1].rstrip() + "…"


def notify_delivery_update(order, delivery_status):
    messages = {
        "assigned": "A driver has been assigned to your order.",
        "picked_up": "Your order has been picked up and is on its way.",
        "delivered": "Your order has been delivered by the driver.",
    }

    _emit(
        order.user_id,
        notification_type="delivery_update",
        title=f"Delivery update for order #{order.id}",
        message=messages.get(
            delivery_status, f"Delivery status: {delivery_status}."
        ),
        link=_order_link(order),
    )
