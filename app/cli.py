"""Custom Flask CLI commands.

These run with `flask <command>` and require server/database access, so they
are the safe place to perform privileged actions that must never be exposed
through a public HTTP endpoint (e.g. creating an administrator).
"""

import os
import uuid

import click
from flask import current_app
from flask.cli import with_appcontext
from werkzeug.security import generate_password_hash

from app import seed_data
from app.extensions import db
from app.models import (
    Address,
    Category,
    Order,
    OrderItem,
    Product,
    ProductImage,
    Store,
    StoreAnnouncement,
    StoreHours,
    User,
)

VALID_VERIFICATION_METHODS = ("email", "sms", "whatsapp")
MIN_ADMIN_PASSWORD_LENGTH = 8


@click.command("create-admin")
@click.option("--email", required=True, prompt=True,
              help="Admin email address.")
@click.option(
    "--password",
    required=True,
    prompt=True,
    hide_input=True,
    confirmation_prompt=True,
    help="Admin password (min 8 characters).",
)
@click.option("--first-name", required=True, prompt="First name")
@click.option("--last-name", required=True, prompt="Last name")
@click.option("--phone", required=True,
              prompt=True, help="Admin phone number.")
@click.option(
    "--verification-method",
    default="email",
    show_default=True,
    type=click.Choice(VALID_VERIFICATION_METHODS),
    help="Channel used for the login verification code.",
)
@with_appcontext
def create_admin(
    email,
    password,
    first_name,
    last_name,
    phone,
    verification_method,
):
    """Create an administrator account.

    Administrators cannot be created through public registration. This command
    is the only supported way to bootstrap the first admin.
    """
    email = (email or "").strip().lower()

    if len(password) < MIN_ADMIN_PASSWORD_LENGTH:
        raise click.ClickException(
            "Password must be at least "
            f"{MIN_ADMIN_PASSWORD_LENGTH} characters."
        )

    existing = User.query.filter_by(email=email).first()

    if existing:
        raise click.ClickException(
            f"A user with email {email} already exists "
            f"(id={existing.id}, role={existing.role})."
        )

    admin = User(
        first_name=first_name.strip(),
        last_name=last_name.strip(),
        email=email,
        password=generate_password_hash(password),
        phone=phone.strip(),
        role="admin",
        # Admins are created out of band by a trusted operator, so the account
        # is verified immediately (no registration email challenge).
        is_verified=True,
        verification_method=verification_method,
    )

    db.session.add(admin)
    db.session.commit()

    click.echo(
        f"Admin account created: {admin.email} (id={admin.id}). "
        f"Login sends a verification code via '{verification_method}'."
    )


DEMO_PASSWORD = "Cedar!2026"
ADMIN_EMAIL = "admin@cedarlink.demo"

# Distinct fill colours for the generated placeholder images.

_IMAGE_COLORS = (
    (198, 40, 40),
    (2, 119, 189),
    (46, 125, 50),
    (245, 124, 0),
    (106, 27, 154),
    (0, 131, 143),
    (191, 54, 12),
    (69, 90, 100),
)


def _refuse_in_production():
    if os.getenv("FLASK_CONFIG", "").strip().lower() == "production":
        raise click.ClickException(
            "`flask seed` is disabled when FLASK_CONFIG=production."
        )


def _get_or_create(model, defaults=None, **filters):
    instance = model.query.filter_by(**filters).first()

    if instance is not None:
        return instance, False

    params = dict(filters)
    params.update(defaults or {})

    instance = model(**params)
    db.session.add(instance)

    return instance, True


def _get_or_create_user(email, first_name, last_name, phone, role):
    user = User.query.filter_by(email=email).first()

    if user is not None:
        return user, False

    user = User(
        first_name=first_name,
        last_name=last_name,
        email=email,
        password=generate_password_hash(DEMO_PASSWORD),
        phone=phone,
        role=role,
        is_verified=True,
        verification_method="email",
    )
    db.session.add(user)

    return user, True


def _placeholder_image(text, color):
    from PIL import Image, ImageDraw, ImageFont

    width, height = 800, 600
    image = Image.new("RGB", (width, height), color)
    draw = ImageDraw.Draw(image)
    font = ImageFont.load_default(size=44)

    lines = []
    line = ""

    for word in text.split():
        candidate = f"{line} {word}".strip()

        if draw.textlength(candidate, font=font) <= width - 80:
            line = candidate
        else:
            if line:
                lines.append(line)
            line = word

    if line:
        lines.append(line)

    line_height = 58
    start_y = (height - len(lines) * line_height) // 2

    for index, line in enumerate(lines):
        text_width = draw.textlength(line, font=font)
        draw.text(
            ((width - text_width) / 2, start_y + index * line_height),
            line,
            fill="white",
            font=font,
        )

    return image


def _save_product_image(product, color):
    filename = f"{uuid.uuid4().hex}.png"
    path = os.path.join(current_app.config["UPLOAD_FOLDER"], filename)

    _placeholder_image(product.name, color).save(path, format="PNG")

    db.session.add(
        ProductImage(image_url=filename, product_id=product.id)
    )


# --------------------------------------------------------------------------- #
# Demo seed
#
# Everything below writes through the ordinary services, so the aggregates a
# screenshot shows — rating_avg, rating_count, used_count, stock — are the
# numbers the application computes, not numbers typed in here. The one
# exception is backdating: an order's created_at is set after the fact,
# because a demo needs history and checkout can only make things now.
# --------------------------------------------------------------------------- #

# Tables that hold only demo content. --reset empties them in FK-safe order
# so a screenshot session can return to a known state mid-way through.
_RESET_ORDER = (
    "coupon_redemptions",
    "review_reports",
    "reviews",
    # Children of orders, so they go before it: delivery_assignments and
    # payments both hold an orders.id, and payments also holds a
    # payment_methods.id.
    "delivery_assignments",
    "payments",
    "order_items",
    "orders",
    "payment_methods",
    "cart_items",
    "carts",
    "shopping_interests",
    "shopping_preferences",
    "notifications",
    "notification_preferences",
    "product_images",
    "products",
    "store_announcements",
    "store_social_links",
    "store_hours",
    "coupons",
    "stores",
    "addresses",
    "two_factor_recovery_codes",
    "two_factor_challenges",
    "categories",
    "users",
)


def _reset_demo_data():
    """Empty every demo table, children first.

    A plain DELETE rather than drop/create: the schema stays exactly as the
    migrations left it, so a reset cannot silently paper over a missing
    migration.
    """
    from sqlalchemy import text

    for table in _RESET_ORDER:
        exists = db.session.execute(
            text(
                "SELECT 1 FROM sqlite_master "
                "WHERE type='table' AND name=:name"
            ),
            {"name": table},
        ).first()
        if exists:
            db.session.execute(text(f"DELETE FROM {table}"))

    db.session.commit()


def _days_ago(days):
    """Naive UTC, ``days`` in the past — what the timestamp columns hold."""
    from datetime import datetime, timedelta, timezone

    return datetime.now(timezone.utc).replace(tzinfo=None) - timedelta(
        days=days
    )


def _backdate(order, days_ago):
    """Put an order in the past. Checkout can only create it now."""
    placed = _days_ago(days_ago)
    order.created_at = placed
    order.updated_at = placed


def _checkout_cart(customer, line_items, city, coupon_code=None):
    """Put items in the customer's cart and check out for real.

    Real checkout means the stock decrement, the coupon claim, the
    redemption row and the order notification all happen the way they do
    in production — which is the point of seeding through services.
    Returns the created orders.
    """
    from app.models.cart import Cart
    from app.models.cart_item import CartItem
    from app.services import order_service

    cart = Cart.query.filter_by(user_id=customer.id).first()
    if cart is None:
        cart = Cart(user_id=customer.id)
        db.session.add(cart)
        db.session.flush()

    CartItem.query.filter_by(cart_id=cart.id).delete()
    for product, quantity in line_items:
        db.session.add(
            CartItem(
                cart_id=cart.id, product_id=product.id, quantity=quantity
            )
        )
    cart.coupon_code = None
    db.session.flush()

    address = customer.addresses[0] if customer.addresses else None
    result = order_service.checkout(
        customer.id,
        address.address_line if address else "Main Street",
        city,
        coupon_code,
    )

    return [
        db.session.get(Order, entry["id"]) for entry in result["orders"]
    ]


def _seed_stores(categories):
    """Vendors, stores, announcements and products.

    Hours and overrides are applied later, by _apply_schedules.
    """
    from datetime import datetime, timedelta, timezone

    from app.services import announcement_service, store_service

    products = {}
    stores = {}
    color_index = 0

    for spec in seed_data.STORE_SPECS:
        vendor, _ = _get_or_create_user(
            spec["vendor_email"],
            spec["vendor_name"][0],
            spec["vendor_name"][1],
            spec["phone"],
            "vendor",
        )
        db.session.flush()

        store, _ = _get_or_create(
            Store,
            {
                "description": spec["description"],
                "location": spec["city"],
                "contact_info": spec["vendor_email"],
                "is_active": spec["active"],
                "approval_status": spec["approval"],
                "inside_city_delivery_fee": spec["inside_fee"],
                "outside_city_delivery_fee": spec["outside_fee"],
                "delivery_available": True,
                "is_online_only": spec.get("online_only", False),
                "latitude": spec.get("lat"),
                "longitude": spec.get("lng"),
            },
            owner_id=vendor.id,
            name=spec["store"],
        )
        db.session.flush()
        stores[spec["store"]] = store

        # Open around the clock *for now*. The real schedules and the
        # override go on at the end, after the seeded checkouts have run —
        # a split day, a 20:00-02:00 window and a "closed for a power
        # outage" override would otherwise make the seed succeed or fail
        # depending on what time of day it was run. See _apply_schedules.
        store_service.replace_hours(
            store,
            [
                # 00:00-23:59 rather than 00:00-00:00: the service
                # rejects equal times, and one minute of downtime a day
                # cannot collide with a seed run.
                {"day_of_week": d, "opens_at": "00:00",
                 "closes_at": "23:59"}
                for d in range(7)
            ],
        )

        now = datetime.now(timezone.utc)

        for entry in spec["announcements"]:
            when = entry["when"]
            data = {"title": entry["title"], "body": entry["body"]}

            if when == "scheduled":
                data["starts_at"] = (now + timedelta(days=6)).isoformat()
                data["ends_at"] = (now + timedelta(days=20)).isoformat()
            elif when == "expired":
                data["starts_at"] = (now - timedelta(days=30)).isoformat()
                data["ends_at"] = (now - timedelta(days=9)).isoformat()
            else:
                data["starts_at"] = (now - timedelta(days=3)).isoformat()

            announcement_service.create(store, data)

        # Through the service, so the values in the demo database are the
        # normalised ones a real vendor submission produces.
        if spec.get("social"):
            store_service.replace_social_links(
                store,
                [
                    {"platform": platform, "value": value}
                    for platform, value in spec["social"]
                ],
            )

        for item in spec["products"]:
            name, description = item["name"], item["description"]
            product, _ = _get_or_create(
                Product,
                {
                    "name_ar": name["ar"],
                    "name_fr": name["fr"],
                    "description_en": description["en"],
                    "description_ar": description["ar"],
                    "description_fr": description["fr"],
                    "price": item["price"],
                    "stock": item["stock"],
                    "category_id": categories[item["category"]].id,
                },
                store_id=store.id,
                name_en=name["en"],
            )
            products[name["en"]] = product

    db.session.flush()

    for product in products.values():
        if not product.images:
            _save_product_image(
                product, _IMAGE_COLORS[color_index % len(_IMAGE_COLORS)]
            )
            color_index += 1

    db.session.commit()
    return stores, products


def _apply_schedules(stores):
    """Put the real opening hours and the override on, last.

    Deliberately after the seeded checkouts: `assert_store_accepts_orders` is a real
    rule, so a store that is genuinely shut cannot be ordered from. Running
    this at the end means the demo gets its interesting schedules without
    the seed's success depending on the clock.
    """
    from datetime import datetime, timedelta, timezone

    from app.services import store_service

    now = datetime.now(timezone.utc)

    for spec in seed_data.STORE_SPECS:
        store = stores[spec["store"]]

        # Through the service, so a split day and a wrap-around interval
        # are validated exactly as a vendor's own edit would be.
        store_service.replace_hours(store, spec["hours"])

        if spec.get("override"):
            override = spec["override"]
            store_service.set_override(
                store,
                override["status"],
                override["reason"],
                until=(
                    now + timedelta(hours=override["hours_ahead"])
                ).isoformat(),
            )

    db.session.commit()


def _seed_customers(categories):
    """Customers, their saved addresses and their stated interests."""
    from app.services import shopping_preferences_service

    customers = []

    for spec in seed_data.CUSTOMER_SPECS:
        customer, _ = _get_or_create_user(
            spec["email"],
            spec["name"][0],
            spec["name"][1],
            spec["phone"],
            "customer",
        )
        db.session.flush()
        customers.append(customer)

        if not customer.addresses:
            for label, line, city, is_default, lat, lng in spec["addresses"]:
                db.session.add(
                    Address(
                        user_id=customer.id,
                        label=label,
                        recipient_name=(
                            f"{customer.first_name} {customer.last_name}"
                        ),
                        phone=customer.phone,
                        address_line=line,
                        city=city,
                        is_default=is_default,
                        latitude=lat,
                        longitude=lng,
                    )
                )

        # Interests through the service so the rows and their order come
        # out exactly as a save from the settings page would leave them.
        if spec["interests"] or spec["hide_out_of_stock"]:
            prefs = shopping_preferences_service.get_or_create_preferences(
                customer.id
            )
            ok, error = shopping_preferences_service.apply_preference_updates(
                prefs,
                {
                    "interest_category_ids": [
                        categories[name].id for name in spec["interests"]
                    ],
                    "hide_out_of_stock": spec["hide_out_of_stock"],
                },
            )
            if not ok:
                raise click.ClickException(f"seed interests: {error}")

    db.session.commit()
    return customers


def _seed_coupons(stores):
    """One coupon per badge state.

    ``used_count`` is never written here — the exhausted coupon reaches its
    limit by actually being redeemed at checkout (ADR 0021), so the number
    on screen is one the application counted.
    """
    from datetime import datetime, timedelta, timezone

    from app.models.coupon import Coupon
    from app.services import coupon_service

    now = datetime.now(timezone.utc).replace(tzinfo=None)
    created = {}

    for spec in seed_data.COUPON_SPECS:
        starts_at = ends_at = None
        is_active = True

        if spec["state"] == "expired":
            starts_at = now - timedelta(days=60)
            ends_at = now - timedelta(days=5)
        elif spec["state"] == "scheduled":
            starts_at = now + timedelta(days=10)
            ends_at = now + timedelta(days=40)

        coupon, _ = _get_or_create(
            Coupon,
            {
                "discount_type": spec["discount_type"],
                "value": spec["value"],
                "min_order_total": spec["min_order_total"],
                "starts_at": starts_at,
                "ends_at": ends_at,
                "usage_limit": spec["usage_limit"],
                "per_user_limit": spec["per_user_limit"],
                "used_count": 0,
                "is_active": is_active,
                "store_id": (
                    stores[spec["store"]].id if spec["store"] else None
                ),
            },
            code=coupon_service.normalize_code(spec["code"]),
        )
        created[spec["code"]] = coupon

    db.session.commit()
    return created


def _seed_orders(customers, stores, products):
    """History across every status, plus the two orders that must be real.

    The plain history is written directly and backdated — a month of past
    orders cannot come out of a checkout that runs today without emptying
    the shelves. The coupon order and the multi-store order *do* go through
    checkout, because their point is the redemption row and the two-order
    split, which only the real path produces.

    Returns the history orders keyed by ``(customer index, store name)``, so
    the delivery seeding can attach a driver to a named one rather than
    guessing at a query.
    """
    history = {}

    for (
        customer_index,
        store_name,
        status,
        line_item_specs,
        days_ago,
    ) in seed_data.ORDER_SPECS:
        customer = customers[customer_index]
        store = stores[store_name]
        line_items = [
            (products[name], quantity) for name, quantity in line_item_specs
        ]
        history[(customer_index, store_name)] = _seed_history_order(
            customer, store, status, line_items, days_ago
        )

    db.session.commit()

    spec = seed_data.COUPON_ORDER
    coupon_orders = _checkout_cart(
        customers[spec["customer"]],
        [(products[n], q) for n, q in spec["items"]],
        spec["city"],
        spec["coupon"],
    )
    for order in coupon_orders:
        order.status = "delivered"
        _backdate(order, 6)
    db.session.commit()

    # A second real checkout, this one against a usage_limit of 1, so that
    # coupon reaches "Limit reached" by being spent rather than by being
    # told it was.
    exhausted = next(
        s for s in seed_data.COUPON_SPECS if s["state"] == "exhausted"
    )
    _checkout_cart(
        customers[2],
        [(products["Leather Belt, Hand-Tooled"], 1)],
        "Tripoli",
        exhausted["code"],
    )
    db.session.commit()

    spec = seed_data.MULTI_STORE_ORDER
    multi = _checkout_cart(
        customers[spec["customer"]],
        [(products[n], q) for n, q in spec["items"]],
        spec["city"],
    )
    for order in multi:
        _backdate(order, 4)
    db.session.commit()

    return history


def _seed_delivery_assignments(history):
    """Drivers on a handful of orders, through delivery_service.

    Every assignment walks the real ``assigned → picked_up → delivered``
    path one step at a time, so the notifications, the delivered timestamp
    and the refusal to skip a step are all exercised exactly as they are
    when a vendor clicks through the console. The rows are then backdated,
    which the service has no reason to allow.

    The point of the set is ADR 0019: one customer with a delivery still
    out — she sees the driver's name and his phone number — and a finished
    one where the number has been withdrawn and only the name remains.
    """
    from app.services import delivery_service

    created = []

    for (
        customer_index,
        store_name,
        driver_name,
        driver_phone,
        final_status,
        assigned_days_ago,
        delivered_days_ago,
    ) in seed_data.DELIVERY_SPECS:
        order = history.get((customer_index, store_name))

        if order is None:
            raise click.ClickException(
                f"seed: no order for delivery spec "
                f"({customer_index}, {store_name!r}) — DELIVERY_SPECS must "
                f"name a customer and store pair that ORDER_SPECS creates.")

        if order.delivery_assignment is not None:
            created.append(order.delivery_assignment)
            continue

        assignment = delivery_service.assign_driver(
            order, driver_name, driver_phone
        )

        step = assignment.status
        while step != final_status:
            step = delivery_service.DELIVERY_STATUS_TRANSITIONS[step]
            delivery_service.advance_status(assignment, order, step)

        assignment.assigned_at = _days_ago(assigned_days_ago)

        if delivered_days_ago is not None:
            assignment.delivered_at = _days_ago(delivered_days_ago)

        created.append(assignment)

    db.session.commit()

    return created


def _seed_history_order(customer, store, status, line_items, days_ago):
    """A past order, written directly and backdated."""
    from datetime import datetime, timedelta, timezone

    address = customer.addresses[0] if customer.addresses else None
    delivery_city = address.city if address else store.location
    delivery_address = address.address_line if address else "Main Street"

    subtotal = sum(
        float(product.price) * quantity for product, quantity in line_items
    )

    if delivery_city.strip().lower() == store.location.strip().lower():
        delivery_fee = float(store.inside_city_delivery_fee)
    else:
        delivery_fee = float(store.outside_city_delivery_fee)

    placed_at = datetime.now(timezone.utc).replace(
        tzinfo=None
    ) - timedelta(days=days_ago)

    order = Order(
        user_id=customer.id,
        store_id=store.id,
        status=status,
        delivery_address=delivery_address,
        delivery_city=delivery_city,
        total_price=subtotal + delivery_fee,
        delivery_fee=delivery_fee,
        created_at=placed_at,
        updated_at=placed_at,
    )
    db.session.add(order)
    db.session.flush()

    for product, quantity in line_items:
        db.session.add(
            OrderItem(
                order_id=order.id,
                product_id=product.id,
                quantity=quantity,
                unit_price=product.price,
            )
        )

    return order


def _seed_reviews(customers, products, stores):
    """Reviews through review_service, so every rating_avg is computed.

    Then one report and one removal, so the admin moderation queue has a
    flagged item to act on and a removed item to show as already handled.
    """
    from app.services import review_service

    written = {}

    for customer_index, (kind, name), rating, title, body in (
        seed_data.REVIEW_SPECS
    ):
        customer = customers[customer_index]

        if kind == "product":
            entity = products[name]
            store = entity.store
            target = {"product_id": entity.id}
        else:
            store = stores[name]
            target = {"store_id": store.id}

        order = Order.query.filter_by(
            user_id=customer.id, store_id=store.id, status="delivered"
        ).first()
        if order is None:
            continue

        already = review_service.Review.query.filter_by(
            user_id=customer.id,
            order_id=order.id,
            product_id=target.get("product_id"),
            store_id=target.get("store_id"),
        ).first()
        if already is not None:
            written[(kind, name)] = already
            continue

        written[(kind, name)] = review_service.create_review(
            customer, order.id, target, rating, title, body
        )

    db.session.commit()

    flagged = written.get(seed_data.FLAGGED_REVIEW)
    if flagged is not None and not flagged.reports:
        reporter = next(
            (c for c in customers if c.id != flagged.user_id), None
        )
        if reporter is not None:
            review_service.report_review(
                reporter, flagged.id, seed_data.FLAG_REASON
            )
            db.session.commit()

    removed = written.get(seed_data.REMOVED_REVIEW)
    if removed is not None and removed.status != "removed":
        review_service.moderate_review(
            removed.id, "remove", seed_data.REMOVE_REASON
        )
        db.session.commit()

    return written


def _seed_notifications(customers):
    """Make sure at least one customer's feed has something in it.

    Checkout already emits an order notification, so this only tops up the
    kinds a seeded history would otherwise never produce.
    """
    from app.services import notification_service

    customer = customers[0]

    # Additive, not all-or-nothing: checkout has already left an order
    # notification in this feed, and skipping on "has any" would mean the
    # demo feed is a single line. Keyed on the types added here so a
    # re-run does not duplicate them.
    existing = {n.type for n in customer.notifications}

    if "order_delivered" not in existing:
        notification_service.create_notification(
            user_id=customer.id,
            category="order_updates",
            notification_type="order_delivered",
            title="Your order has been delivered",
            message="Hamra Grocery marked your order as delivered. "
                    "You can review what you received.",
            link="/orders",
        )

    if "store_announcement" not in existing:
        notification_service.create_notification(
            user_id=customer.id,
            category="promotions",
            notification_type="store_announcement",
            title="Hamra Grocery posted an update",
            message="New olive-oil pressing just arrived.",
            link="/stores",
        )

    db.session.commit()

    if not customer.notifications:
        raise click.ClickException(
            "seed: no notifications were created — create_notification "
            "returns None for an unknown category rather than raising, so "
            "check the category names against notification_service."
        )


@click.command("seed")
@click.option(
    "--reset",
    is_flag=True,
    help="Empty the demo tables first. Use this to return a half-finished "
         "screenshot session to a known state.",
)
@with_appcontext
def seed(reset):
    """Populate the database with a realistic demo marketplace.

    Re-runnable: plain `flask seed` fills in whatever is missing, and
    `flask seed --reset` clears the demo tables and rebuilds from scratch.
    Refuses to run when FLASK_CONFIG=production.
    """
    _refuse_in_production()

    if reset:
        _reset_demo_data()
        click.echo("Demo tables emptied.")

    _get_or_create_user(
        ADMIN_EMAIL, "Site", "Admin", "+961 1 000 000", "admin"
    )
    db.session.flush()

    categories = {}
    for name_en, name_ar, name_fr in seed_data.CATEGORY_SPECS:
        category, _ = _get_or_create(
            Category,
            {
                "name_ar": name_ar,
                "name_fr": name_fr,
                "description": f"{name_en} from local Lebanese stores.",
            },
            name_en=name_en,
        )
        categories[name_en] = category
    db.session.commit()

    stores, products = _seed_stores(categories)
    customers = _seed_customers(categories)
    coupons = _seed_coupons(stores)
    history = _seed_orders(customers, stores, products)
    _seed_delivery_assignments(history)
    _apply_schedules(stores)
    _seed_reviews(customers, products, stores)
    _seed_notifications(customers)

    _report(stores, products, customers, coupons)


def _report(stores, products, customers, coupons):
    """What was created, and how to log in as each role."""
    from app.models.coupon import Coupon
    from app.models.coupon_redemption import CouponRedemption
    from app.models.delivery_assignment import DeliveryAssignment
    from app.models.review import Review
    from app.models.store_social_link import StoreSocialLink
    from app.models.shopping_interest import ShoppingInterest

    counts = (
        ("Categories", Category.query.count()),
        ("Stores", Store.query.count()),
        ("Products", Product.query.count()),
        ("Store hours rows", StoreHours.query.count()),
        ("Announcements", StoreAnnouncement.query.count()),
        ("Social links", StoreSocialLink.query.count()),
        ("Orders", Order.query.count()),
        ("Delivery assignments", DeliveryAssignment.query.count()),
        ("Reviews", Review.query.count()),
        ("Coupons", Coupon.query.count()),
        ("Coupon redemptions", CouponRedemption.query.count()),
        ("Addresses", Address.query.count()),
        ("Interests", ShoppingInterest.query.count()),
    )

    click.echo("")
    click.echo("=" * 68)
    click.echo("CedarLink demo data is ready.")
    click.echo("")
    for label, value in counts:
        click.echo(f"  {label:<22} {value}")

    click.echo("")
    click.echo(f"Sign in with any of these — password: {DEMO_PASSWORD}")
    click.echo("")
    click.echo(f"  admin     {ADMIN_EMAIL}")
    click.echo(
        f"  vendor    {seed_data.STORE_SPECS[0]['vendor_email']:<38}"
        f"{seed_data.STORE_SPECS[0]['store']}"
    )
    click.echo(
        f"  customer  {seed_data.CUSTOMER_SPECS[0]['email']:<38}"
        f"{seed_data.CUSTOMER_SPECS[0]['name'][0]} "
        f"{seed_data.CUSTOMER_SPECS[0]['name'][1]}"
    )
    click.echo("")
    click.echo("Every other demo vendor and customer uses the same password;")
    click.echo("the full list is in the README.")
    click.echo("")
    click.echo(
        "Logging in sends a 6-digit code. With MAIL_SUPPRESS_SEND=true "
        "(the .env.example"
    )
    click.echo("default) the code is printed to the Flask server console.")
    click.echo("=" * 68)


def register_cli(app):
    app.cli.add_command(create_admin)
    app.cli.add_command(seed)
