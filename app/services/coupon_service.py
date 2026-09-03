"""Coupon validation, eligibility and redemption.

Validation and eligibility live here; *application* — turning an eligible
coupon into money off — lives in ``order_service.price_cart``, because
pricing exists in exactly one place (CL-15) and a discount is part of a
price.

Every rejection carries its own ``code`` so an interface can say why rather
than "invalid coupon". See docs/decisions/0021-coupons-and-discounts.md.
"""

from datetime import datetime, timezone
from decimal import ROUND_HALF_UP, Decimal

from sqlalchemy import func, select, update

from app.extensions import db
from app.models.coupon import FIXED, PERCENTAGE, Coupon
from app.models.coupon_redemption import CouponRedemption

CENTS = Decimal("0.01")


class CouponError(Exception):
    """A coupon that cannot be applied, and exactly why.

    ``code`` is the machine-readable reason. The route returns it verbatim
    so the client can phrase its own message per reason; ``message`` is the
    English fallback.
    """

    def __init__(self, code, message, status_code=400, **extra):
        super().__init__(message)
        self.code = code
        self.status_code = status_code
        self.payload = {"error": message, "code": code, **extra}


# One constant per rejection reason — referenced by the tests, so a
# renamed code breaks the build rather than silently changing the API.
UNKNOWN = "coupon_unknown"
INACTIVE = "coupon_inactive"
NOT_STARTED = "coupon_not_started"
EXPIRED = "coupon_expired"
BELOW_MINIMUM = "coupon_below_minimum"
USAGE_LIMIT = "coupon_usage_limit"
USER_LIMIT = "coupon_user_limit"
WRONG_STORE = "coupon_wrong_store"
FIXED_MULTI_STORE = "coupon_fixed_multi_store"


def _now():
    """Seam for tests, and the one place UTC now is read on this path."""
    return datetime.now(timezone.utc)


def _as_utc(value):
    """A stored datetime as aware UTC.

    SQLite hands back a naive value for an aware one that was written, so
    comparing it to an aware ``_now()`` would raise. Naive means UTC here
    because that is the only thing ever written.
    """
    if value is None:
        return None
    return value if value.tzinfo is not None else value.replace(
        tzinfo=timezone.utc
    )


def normalize_code(code):
    """Trimmed and uppercased — the stored form, and the match form.

    Storing the normalised code means the unique index *is* the
    case-insensitive lookup: no ``LOWER()`` on the column, no dependence on
    the database's collation, and no chance of two coupons whose codes
    differ only in case.
    """
    return str(code or "").strip().upper()


def find_by_code(code):
    """The coupon for a raw user-supplied code, or None."""
    normalized = normalize_code(code)

    if not normalized:
        return None

    return Coupon.query.filter_by(code=normalized).first()


def _money(value):
    return Decimal(value).quantize(CENTS, rounding=ROUND_HALF_UP)


def discount_for(coupon, goods_subtotal):
    """Money off a goods subtotal, clamped to it.

    Never applied to a delivery fee, and never larger than the goods it is
    discounting — which is what keeps a total from going negative.
    """
    goods_subtotal = Decimal(goods_subtotal)

    if goods_subtotal <= 0:
        return Decimal("0.00")

    if coupon.discount_type == PERCENTAGE:
        raw = goods_subtotal * (Decimal(coupon.value) / Decimal("100"))
    else:
        raw = Decimal(coupon.value)

    return min(_money(raw), _money(goods_subtotal))


def redemption_count(coupon_id, user_id):
    """How many times this user has redeemed this coupon."""
    return db.session.execute(
        select(func.count())
        .select_from(CouponRedemption)
        .where(
            CouponRedemption.coupon_id == coupon_id,
            CouponRedemption.user_id == user_id,
        )
    ).scalar_one()


def validate_for_cart(code, user, cart_groups):
    """The eligible coupon for this cart, or ``CouponError`` saying why not.

    ``cart_groups`` is ``price_cart``'s per-store list — each entry needs
    ``store_id`` and ``subtotal`` (goods only). Checks run in a deliberate
    order: what the coupon *is* before what the cart *is*, so a customer is
    told the code is expired rather than that their basket is too small.
    """
    coupon = find_by_code(code)

    if coupon is None:
        raise CouponError(UNKNOWN, "That coupon code was not recognised", 404)

    if not coupon.is_active:
        raise CouponError(INACTIVE, "That coupon is no longer available")

    now = _now()

    starts_at = _as_utc(coupon.starts_at)
    if starts_at is not None and now < starts_at:
        raise CouponError(NOT_STARTED, "That coupon is not active yet")

    ends_at = _as_utc(coupon.ends_at)
    if ends_at is not None and now >= ends_at:
        raise CouponError(EXPIRED, "That coupon has expired")

    # Which goods the coupon can see: its own store's, or the whole cart.
    if coupon.store_id is not None:
        eligible = [
            group for group in cart_groups
            if group["store_id"] == coupon.store_id
        ]
        if not eligible:
            raise CouponError(
                WRONG_STORE,
                "That coupon only applies to another store",
                store_id=coupon.store_id,
            )
    else:
        eligible = list(cart_groups)

        # A fixed amount has no defensible split across stores — see the
        # ADR. Percentages do, so only the fixed kind is refused.
        if coupon.discount_type == FIXED and len(eligible) > 1:
            raise CouponError(
                FIXED_MULTI_STORE,
                "That coupon cannot be used on an order from more than "
                "one store",
            )

    # A use is consumed per *order*, and this cart becomes one order per
    # store, so the limits are checked against how many orders the coupon
    # will actually be redeemed on. Checking against 1 here would let a
    # preview succeed where the checkout then fails — the quote/charge
    # drift CL-15 exists to prevent.
    orders = len(eligible)

    if (
        coupon.usage_limit is not None
        and coupon.used_count + orders > coupon.usage_limit
    ):
        raise CouponError(USAGE_LIMIT, "That coupon has been fully redeemed")

    if coupon.per_user_limit is not None and user is not None:
        used = redemption_count(coupon.id, user.id)
        if used + orders > coupon.per_user_limit:
            raise CouponError(
                USER_LIMIT, "You have already used that coupon"
            )

    goods_subtotal = sum(
        (Decimal(group["subtotal"]) for group in eligible), Decimal("0")
    )

    # Before the discount, deliberately: a coupon must not be able to pull
    # a basket under its own minimum and then still apply.
    if (
        coupon.min_order_total is not None
        and goods_subtotal < Decimal(coupon.min_order_total)
    ):
        raise CouponError(
            BELOW_MINIMUM,
            "Your order is below the minimum for that coupon",
            min_order_total=float(coupon.min_order_total),
            goods_subtotal=float(goods_subtotal),
        )

    return coupon


# --------------------------------------------------------------------------- #
# Redemption — claimed with conditional statements, never read-then-write
# --------------------------------------------------------------------------- #

def claim(coupon, user_id):
    """Take one use of ``coupon`` for ``user_id``.

    The overall limit is claimed in a single statement:

    ``UPDATE coupons SET used_count = used_count + 1
      WHERE id = :id AND (usage_limit IS NULL OR used_count < usage_limit)``

    A rowcount of 0 means somebody else took the last one between pricing
    and here — the fourth appearance of the lost-update pattern in this
    codebase (ADR 0007). Raises the same errors the pre-check raises, so a
    caller that loses the race gets the message it would have got a moment
    earlier.
    """
    claimed = db.session.execute(
        update(Coupon)
        .where(
            Coupon.id == coupon.id,
            db.or_(
                Coupon.usage_limit.is_(None),
                Coupon.used_count < Coupon.usage_limit,
            ),
        )
        .values(used_count=Coupon.used_count + 1)
        .execution_options(synchronize_session=False)
    )

    if claimed.rowcount == 0:
        raise CouponError(USAGE_LIMIT, "That coupon has been fully redeemed")

    # The per-user limit has no counter column to increment — it is a count
    # of redemption rows — so it is claimed by inserting the row and then
    # re-counting inside the same transaction. A concurrent duplicate is
    # still uncommitted and therefore invisible, so the loser of a race
    # sees its own row plus the winner's only after the winner commits;
    # SQLite serialises the writes, and the check is repeated here rather
    # than trusted from validate_for_cart.
    if coupon.per_user_limit is not None:
        if redemption_count(coupon.id, user_id) >= coupon.per_user_limit:
            raise CouponError(
                USER_LIMIT, "You have already used that coupon"
            )


def release(coupon_id, order_id):
    """Undo a redemption when a pending order is cancelled.

    Deletes the redemption row and decrements ``used_count``, the same way
    cancelling restores stock. The decrement is guarded so a double
    cancellation cannot drive the counter below zero.
    """
    deleted = db.session.execute(
        CouponRedemption.__table__.delete().where(
            CouponRedemption.coupon_id == coupon_id,
            CouponRedemption.order_id == order_id,
        )
    )

    if deleted.rowcount == 0:
        return

    db.session.execute(
        update(Coupon)
        .where(Coupon.id == coupon_id, Coupon.used_count >= deleted.rowcount)
        .values(used_count=Coupon.used_count - deleted.rowcount)
        .execution_options(synchronize_session=False)
    )


def record(coupon, user_id, order_id, amount_applied):
    """Write the audit row. Caller commits, with the order."""
    redemption = CouponRedemption(
        coupon_id=coupon.id,
        user_id=user_id,
        order_id=order_id,
        amount_applied=_money(amount_applied),
    )
    db.session.add(redemption)
    return redemption
