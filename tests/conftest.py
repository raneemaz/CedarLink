"""Shared test fixtures.

Layout:
  * ``app``      — one application on TestConfig for the whole run, holding a
                   single pushed app context so test-client requests reuse its
                   SQLAlchemy session (data a request commits is visible to
                   the assertions immediately).
  * ``_schema``  — session-scoped; creates the schema once.
  * ``_reset_db``— autouse; empties every table after each test, so tests are
                   fully isolated without paying DDL cost per test.
  * factories    — ``make_user`` / ``make_store`` / ``make_category`` /
                   ``make_product`` / ``make_order`` plus the ``customer`` /
                   ``vendor`` / ``admin`` shortcuts.
  * ``auth``     — mints a JWT directly via ``create_access_token`` so tests
                   skip the 2FA challenge. Exactly one test
                   (test_register_verify_login_full_flow) walks the real flow.
"""

import functools
from datetime import time

import pytest
from flask_jwt_extended import create_access_token
from werkzeug.security import generate_password_hash as _hash

from app import create_app
from app.config import TestConfig
from app.extensions import db as _db
from app.extensions import limiter as _limiter
from app.models.category import Category
from app.models.order import Order
from app.models.order_item import OrderItem
from app.models.product import Product
from app.models.store import Store
from app.models.store_hours import StoreHours
from app.models.user import User

# Cheap, deterministic hashing for factory users — keeps the suite fast.
# check_password_hash() verifies any scheme, so login still works end to end.
fast_hash = functools.partial(_hash, method="pbkdf2:sha256:1")


@pytest.fixture(scope="session")
def app(tmp_path_factory):
    db_path = tmp_path_factory.mktemp("db") / "test.db"
    uploads = tmp_path_factory.mktemp("uploads")

    class _TestConfig(TestConfig):
        SQLALCHEMY_DATABASE_URI = f"sqlite:///{db_path.as_posix()}"
        UPLOAD_FOLDER = str(uploads)

    application = create_app(_TestConfig)
    ctx = application.app_context()
    ctx.push()
    try:
        yield application
    finally:
        _db.session.remove()
        ctx.pop()


@pytest.fixture(scope="session")
def _schema(app):
    _db.create_all()
    yield
    _db.session.remove()
    _db.drop_all()


@pytest.fixture(autouse=True)
def _reset_db(_schema):
    """Empty every table around each test — full isolation, no DDL churn."""
    yield
    _db.session.remove()
    for table in reversed(_db.metadata.sorted_tables):
        _db.session.execute(table.delete())
    _db.session.commit()


@pytest.fixture(autouse=True)
def _rate_limits_off():
    """Throttling is opt-in per test.

    The limiter is installed (TestConfig sets RATELIMIT_ENABLED) so its code
    path runs, but in-memory counters are shared across the whole session
    and cannot be reliably reset, so every test starts with limiting off.
    The `rate_limiting` fixture turns it on for the few tests that need it.
    """
    _limiter.enabled = False
    yield
    _limiter.enabled = False


@pytest.fixture()
def rate_limiting():
    """Enable auth-endpoint throttling for this test."""
    try:
        _limiter.storage.reset()
    except Exception:
        pass
    _limiter.enabled = True
    yield
    _limiter.enabled = False


@pytest.fixture()
def db(_reset_db):
    return _db


@pytest.fixture()
def client(app):
    return app.test_client()


@pytest.fixture()
def auth():
    """Return ``{"Authorization": "Bearer ..."}`` for a user, no 2FA."""

    def _auth(user):
        token = create_access_token(
            identity=str(user.id),
            additional_claims={"role": user.role},
        )
        return {"Authorization": f"Bearer {token}"}

    return _auth


# --------------------------------------------------------------------------- #
# Factories
# --------------------------------------------------------------------------- #

@pytest.fixture()
def make_user(_reset_db):
    counter = {"n": 0}

    def _make(role="customer", password="Passw0rd!", **kw):
        n = counter["n"]
        counter["n"] += 1
        user = User(
            first_name=kw.get("first_name", "Test"),
            last_name=kw.get("last_name", role.capitalize()),
            email=kw.get("email", f"{role}{n}@test.local"),
            password=fast_hash(password),
            phone=kw.get("phone", f"+9613{n:06d}"),
            role=role,
            is_verified=kw.get("is_verified", True),
            verification_method=kw.get("verification_method", "email"),
        )
        _db.session.add(user)
        _db.session.commit()
        user.plain_password = password
        return user

    return _make


@pytest.fixture()
def customer(make_user):
    return make_user("customer")


@pytest.fixture()
def vendor(make_user):
    return make_user("vendor")


@pytest.fixture()
def admin(make_user):
    return make_user("admin")


@pytest.fixture()
def make_category(_reset_db):
    counter = {"n": 0}

    def _make(name=None, description="A test category", **kw):
        counter["n"] += 1
        category = Category(
            name_en=name or f"Category {counter['n']}",
            name_ar=kw.get("name_ar"),
            name_fr=kw.get("name_fr"),
            description=description,
        )
        _db.session.add(category)
        _db.session.commit()
        return category

    return _make


@pytest.fixture()
def category(make_category):
    return make_category()


@pytest.fixture()
def make_store(make_user):
    def _make(
        owner=None,
        approval_status="approved",
        is_active=True,
        open_always=True,
        **kw,
    ):
        owner = owner or make_user("vendor")
        store = Store(
            owner_id=owner.id,
            name=kw.get("name", f"{owner.email.split('@')[0]}'s store"),
            description=kw.get("description", "A test store"),
            location=kw.get("location", "Beirut"),
            contact_info=kw.get("contact_info", "store@test.local"),
            inside_city_delivery_fee=kw.get("inside_city_delivery_fee", 2),
            outside_city_delivery_fee=kw.get("outside_city_delivery_fee", 5),
            delivery_available=kw.get("delivery_available", True),
            approval_status=approval_status,
            is_active=is_active,
        )
        _db.session.add(store)
        _db.session.flush()

        # A store with no StoreHours rows is closed. Most tests don't care
        # about hours, so give it a 24/7 schedule by default; the store-hours
        # tests pass open_always=False and set their own.
        if open_always:
            for day in range(7):
                _db.session.add(
                    StoreHours(
                        store_id=store.id,
                        day_of_week=day,
                        opens_at=time(0, 0),
                        closes_at=time(0, 0),
                    )
                )

        _db.session.commit()
        return store

    return _make


@pytest.fixture()
def store(make_store):
    return make_store()


@pytest.fixture()
def make_product(make_store, make_category):
    counter = {"n": 0}

    def _make(store=None, category=None, price=10.0, stock=5, **kw):
        counter["n"] += 1
        store = store or make_store()
        category = category or make_category()
        product = Product(
            name_en=kw.get("name", f"Product {counter['n']}"),
            name_ar=kw.get("name_ar"),
            name_fr=kw.get("name_fr"),
            description_en=kw.get("description", "A test product"),
            description_ar=kw.get("description_ar"),
            description_fr=kw.get("description_fr"),
            price=price,
            stock=stock,
            store_id=store.id,
            category_id=category.id,
        )
        _db.session.add(product)
        _db.session.commit()
        return product

    return _make


@pytest.fixture()
def product(make_product):
    return make_product()


@pytest.fixture()
def make_order(make_user, make_product):
    def _make(
        customer=None,
        product=None,
        quantity=1,
        status="pending",
        decrement_stock=False,
        **kw,
    ):
        customer = customer or make_user("customer")
        product = product or make_product()
        unit_price = product.price
        order = Order(
            user_id=customer.id,
            store_id=product.store_id,
            status=status,
            delivery_address=kw.get("delivery_address", "1 Test Street"),
            delivery_city=kw.get("delivery_city", "Beirut"),
            total_price=float(unit_price) * quantity,
        )
        _db.session.add(order)
        _db.session.flush()
        _db.session.add(
            OrderItem(
                order_id=order.id,
                product_id=product.id,
                quantity=quantity,
                unit_price=unit_price,
            )
        )
        if decrement_stock:
            product.stock -= quantity
        _db.session.commit()
        return order

    return _make


# --------------------------------------------------------------------------- #
# Helpers
# --------------------------------------------------------------------------- #

@pytest.fixture()
def add_to_cart(client, auth):
    """POST a product into a user's cart via the real endpoint."""

    def _add(user, product, quantity=1):
        return client.post(
            "/api/cart/items",
            json={"product_id": product.id, "quantity": quantity},
            headers=auth(user),
        )

    return _add
