"""Account lifecycle: deactivation, reactivation, and anonymizing deletion.

Permanent deletion never removes a user's orders or payments — those are the
vendor's and the platform's financial/audit records. Instead the ``users`` row
is anonymized in place and only the user's private data is purged.
"""

import secrets
from datetime import datetime

from flask import current_app
from werkzeug.security import generate_password_hash

from app.extensions import db
from app.models.address import Address
from app.models.cart import Cart
from app.models.cart_item import CartItem
from app.models.notification import Notification
from app.models.notification_preferences import NotificationPreferences
from app.models.order import Order
from app.models.payment import Payment
from app.models.payment_method import PaymentMethod
from app.models.product import Product
from app.models.shopping_preferences import ShoppingPreferences
from app.models.store import Store
from app.models.two_factor_challenge import TwoFactorChallenge
from app.models.two_factor_recovery_code import TwoFactorRecoveryCode

IN_PROGRESS_ORDER_STATUSES = ("pending", "processing")
DELETED_ADDRESS_SENTINEL = "[deleted]"


class AccountActionBlocked(Exception):
    """Raised when an account action cannot proceed (e.g. open orders)."""

    def __init__(self, message):
        super().__init__(message)
        self.message = message


def deactivate_account(user):
    user.is_active = False

    # A deactivated vendor's storefront goes dark too.
    if user.role == "vendor":
        for store in Store.query.filter_by(owner_id=user.id).all():
            store.is_active = False

    db.session.commit()
    current_app.logger.info("Account deactivated: user_id=%s", user.id)


def reactivate_account(user):
    user.is_active = True
    db.session.commit()
    current_app.logger.info("Account reactivated: user_id=%s", user.id)


def deletion_block_reason(user):
    """Return a message if deletion must be blocked, else None."""
    open_customer_orders = Order.query.filter(
        Order.user_id == user.id,
        Order.status.in_(IN_PROGRESS_ORDER_STATUSES),
    ).count()

    if open_customer_orders:
        return (
            "You have orders in progress. Wait until they are delivered, or "
            "cancel them, before deleting your account."
        )

    if user.role == "vendor":
        store_ids = [
            s.id for s in Store.query.filter_by(owner_id=user.id).all()
        ]
        if store_ids:
            store_orders = Order.query.filter(
                Order.store_id.in_(store_ids)
            ).count()
            if store_orders:
                return (
                    "Your store has order history. Contact support to close a "
                    "store that has received orders."
                )

    return None


def delete_account(user):
    """Anonymize the user row and purge private data in a single transaction.

    Raises ``AccountActionBlocked`` on a failed pre-check; re-raises on any DB
    error after rolling back (the account is left untouched).
    """
    reason = deletion_block_reason(user)
    if reason:
        raise AccountActionBlocked(reason)

    user_id = user.id

    try:
        # Vendor store teardown — only reachable when the store has no orders.
        if user.role == "vendor":
            stores = Store.query.filter_by(owner_id=user_id).all()
            store_ids = [s.id for s in stores]

            if store_ids:
                product_ids = [
                    p.id
                    for p in Product.query.filter(
                        Product.store_id.in_(store_ids)
                    ).all()
                ]
                if product_ids:
                    CartItem.query.filter(
                        CartItem.product_id.in_(product_ids)
                    ).delete(synchronize_session=False)

                for store in stores:
                    db.session.delete(store)  # cascades products + images

        # Detach payments from the saved cards we're about to delete.
        pm_ids = [
            pm.id
            for pm in PaymentMethod.query.filter_by(user_id=user_id).all()
        ]
        if pm_ids:
            Payment.query.filter(
                Payment.payment_method_id.in_(pm_ids)
            ).update(
                {"payment_method_id": None}, synchronize_session=False
            )

        # Purge private child data.
        Address.query.filter_by(user_id=user_id).delete(
            synchronize_session=False
        )
        PaymentMethod.query.filter_by(user_id=user_id).delete(
            synchronize_session=False
        )
        Notification.query.filter_by(user_id=user_id).delete(
            synchronize_session=False
        )
        NotificationPreferences.query.filter_by(user_id=user_id).delete(
            synchronize_session=False
        )
        ShoppingPreferences.query.filter_by(user_id=user_id).delete(
            synchronize_session=False
        )
        TwoFactorChallenge.query.filter_by(user_id=user_id).delete(
            synchronize_session=False
        )
        TwoFactorRecoveryCode.query.filter_by(user_id=user_id).delete(
            synchronize_session=False
        )

        cart = Cart.query.filter_by(user_id=user_id).first()
        if cart:
            db.session.delete(cart)  # cascades cart_items

        # Scrub the delivery address from retained orders.
        Order.query.filter_by(user_id=user_id).update(
            {"delivery_address": DELETED_ADDRESS_SENTINEL},
            synchronize_session=False,
        )

        # Anonymize the user row. It stays because orders reference it and
        # users.id is NOT NULL on the orders foreign key.
        user.first_name = "Deleted"
        user.last_name = "User"
        user.email = f"deleted+{user_id}@users.cedarlink.invalid"
        user.phone = None
        user.password = generate_password_hash(secrets.token_urlsafe(32))
        user.verification_method = None
        user.two_factor_enabled = False
        user.two_factor_method = None
        user.two_factor_totp_secret = None
        user.is_active = False
        user.deleted_at = datetime.utcnow()

        db.session.commit()
        current_app.logger.info(
            "Account deleted (anonymized): user_id=%s", user_id
        )
    except AccountActionBlocked:
        raise
    except Exception:
        db.session.rollback()
        current_app.logger.exception(
            "Account deletion failed: user_id=%s", user_id
        )
        raise
