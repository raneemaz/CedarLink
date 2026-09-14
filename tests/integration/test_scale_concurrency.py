"""Concurrency invariants at 50 threads — measurement, not a fix.

The 2–3 thread races in ``test_concurrent_checkout.py``, ``test_coupons.py``
and ``test_two_factor.py`` prove the *shape* of each guard. This file runs
the same guards at 50 simultaneous clients and adds the three races that
had no coverage: the review rating aggregate, store-name collisions, and a
single customer hammering a ``per_user_limit = 1`` coupon.

Each worker is held at a ``threading.Barrier`` the instant it has read what
it needs and before it writes, then all are released together, so the
result does not depend on scheduling.

The app here is built with a 64-connection pool. The default (``QueuePool``
size 5 + overflow 10 = 15) would cap real parallelism at 15 and a barrier
of 50 would never fill — that ceiling is measured separately in
``scripts/loadtest.py`` and written up in ADR 0032. What is under test here
is the database guard, not the pool.

The conftest ``Engine`` ``connect`` listener (``PRAGMA foreign_keys=ON``)
is global, so it also covers the engine this module builds.
"""

import threading
from datetime import datetime, time as dtime, timedelta

import pyotp
import pytest
from flask_jwt_extended import create_access_token
from werkzeug.security import generate_password_hash

from app import create_app
from app.config import TestConfig
from app.extensions import db as _db
from app.models.cart import Cart
from app.models.cart_item import CartItem
from app.models.category import Category
from app.models.coupon import Coupon
from app.models.coupon_redemption import CouponRedemption
from app.models.order import Order
from app.models.order_item import OrderItem
from app.models.product import Product
from app.models.review import Review
from app.models.store import Store
from app.models.store_hours import StoreHours
from app.models.two_factor_challenge import TwoFactorChallenge
from app.models.user import User
from app.services import coupon_service, two_factor_service
from app.services.two_factor_service import SECURITY_PURPOSE, TOTP_METHOD

N = 50
_FAST_HASH = "pbkdf2:sha256:1"


@pytest.fixture(scope="module")
def scale_app(tmp_path_factory):
    db_path = tmp_path_factory.mktemp("scale") / "scale.db"

    class _Config(TestConfig):
        SQLALCHEMY_DATABASE_URI = f"sqlite:///{db_path.as_posix()}"
        SQLALCHEMY_ENGINE_OPTIONS = {"pool_size": 64, "max_overflow": 16}

    application = create_app(_Config)
    ctx = application.app_context()
    ctx.push()
    _db.create_all()
    try:
        yield application
    finally:
        _db.session.remove()
        _db.drop_all()
        ctx.pop()


@pytest.fixture(autouse=True)
def _reset(scale_app):
    yield
    _db.session.remove()
    for table in reversed(_db.metadata.sorted_tables):
        _db.session.execute(table.delete())
    _db.session.commit()


# --------------------------------------------------------------------------- #
# Direct seeding — independent of the main conftest factories
# --------------------------------------------------------------------------- #

def _user(role="customer", **kw):
    n = User.query.count()
    user = User(
        first_name="T",
        last_name=role,
        email=kw.get("email", f"{role}{n}@scale.local"),
        password=generate_password_hash("pw", method=_FAST_HASH),
        phone=f"+9613{n:06d}",
        role=role,
        is_verified=True,
        verification_method="email",
    )
    _db.session.add(user)
    _db.session.commit()
    return user


def _store(owner=None, name="A Store"):
    owner = owner or _user("vendor")
    store = Store(
        owner_id=owner.id,
        name=name,
        description="d",
        location="Beirut",
        contact_info="s@scale.local",
        approval_status="approved",
        is_active=True,
    )
    _db.session.add(store)
    _db.session.flush()
    for day in range(7):
        _db.session.add(
            StoreHours(
                store_id=store.id,
                day_of_week=day,
                opens_at=dtime(0, 0),
                closes_at=dtime(0, 0),
            )
        )
    _db.session.commit()
    return store


def _product(store, price=10.0, stock=5):
    cat = Category.query.first()
    if cat is None:
        cat = Category(name_en="C", description="c")
        _db.session.add(cat)
        _db.session.commit()
    product = Product(
        name_en="P",
        description_en="d",
        price=price,
        stock=stock,
        store_id=store.id,
        category_id=cat.id,
    )
    _db.session.add(product)
    _db.session.commit()
    return product


def _delivered_order(customer, product):
    order = Order(
        user_id=customer.id,
        store_id=product.store_id,
        status="delivered",
        delivery_address="1 St",
        delivery_city="Beirut",
        total_price=product.price,
    )
    _db.session.add(order)
    _db.session.flush()
    _db.session.add(
        OrderItem(
            order_id=order.id,
            product_id=product.id,
            quantity=1,
            unit_price=product.price,
        )
    )
    _db.session.commit()
    return order


def _put_in_cart(user, product, qty=1):
    cart = Cart(user_id=user.id)
    _db.session.add(cart)
    _db.session.flush()
    _db.session.add(
        CartItem(cart_id=cart.id, product_id=product.id, quantity=qty)
    )
    _db.session.commit()


def _token(scale_app, user):
    with scale_app.app_context():
        raw = create_access_token(
            identity=str(user.id), additional_claims={"role": user.role}
        )
    return {"Authorization": f"Bearer {raw}"}


# --------------------------------------------------------------------------- #
# Thread plumbing
# --------------------------------------------------------------------------- #

def _run(count, target):
    threads = [
        threading.Thread(target=target, args=(i,)) for i in range(count)
    ]
    for thread in threads:
        thread.start()
    for thread in threads:
        thread.join(timeout=90)
    assert not any(t.is_alive() for t in threads), "a worker thread hung"


def _barrier(count):
    return threading.Barrier(count, timeout=60)


def _wait(gate):
    try:
        gate.wait()
    except threading.BrokenBarrierError:
        pass


def _concurrent_checkouts(scale_app, monkeypatch, buyers, coupon_code=None):
    import app.services.order_service as order_service

    real = order_service.price_cart
    gate = _barrier(len(buyers))

    def synced(*a, **k):
        out = real(*a, **k)
        _wait(gate)
        return out

    monkeypatch.setattr(order_service, "price_cart", synced)

    headers = [_token(scale_app, u) for u in buyers]
    results = {}

    def do(i):
        body = {
            "delivery_address": "1 Race St",
            "delivery_city": "Beirut",
            "payment_method": "cash_on_delivery",
        }
        if coupon_code:
            body["coupon_code"] = coupon_code
        results[i] = scale_app.test_client().post(
            "/api/orders", json=body, headers=headers[i]
        ).status_code

    _run(len(buyers), do)
    return results


# --------------------------------------------------------------------------- #
# 1. Existing races, at 50
# --------------------------------------------------------------------------- #

def test_50_checkouts_for_the_last_unit_admit_exactly_one(scale_app, monkeypatch):
    product = _product(_store(), stock=1)
    pid = product.id
    buyers = [_user(email=f"last-{i}@scale.local") for i in range(N)]
    for buyer in buyers:
        _put_in_cart(buyer, product)

    results = _concurrent_checkouts(scale_app, monkeypatch, buyers)

    assert sorted(results.values()).count(201) == 1, results
    _db.session.expire_all()
    assert _db.session.get(Product, pid).stock == 0
    assert OrderItem.query.filter_by(product_id=pid).count() == 1


def test_50_checkouts_against_stock_of_25_admit_exactly_25(scale_app, monkeypatch):
    product = _product(_store(), stock=25)
    pid = product.id
    buyers = [_user(email=f"rush-{i}@scale.local") for i in range(N)]
    for buyer in buyers:
        _put_in_cart(buyer, product)

    results = _concurrent_checkouts(scale_app, monkeypatch, buyers)

    assert sorted(results.values()).count(201) == 25, results
    _db.session.expire_all()
    assert _db.session.get(Product, pid).stock == 0
    assert sum(
        i.quantity for i in OrderItem.query.filter_by(product_id=pid)
    ) == 25


def test_50_checkouts_on_a_usage_limit_1_coupon_admit_exactly_one(
    scale_app, monkeypatch
):
    """Exactly one takes the single use. The other 49 lose the claim's
    conditional UPDATE and the checkout 400s — CedarLink fails the order
    rather than silently dropping the discount, the same as the 2-thread
    test in test_coupons.py.
    """
    product = _product(_store(), stock=N)
    coupon = Coupon(
        code="LAST", discount_type="fixed", value=1, usage_limit=1,
        is_active=True,
    )
    _db.session.add(coupon)
    _db.session.commit()
    cid = coupon.id
    buyers = [_user(email=f"coup-{i}@scale.local") for i in range(N)]
    for buyer in buyers:
        _put_in_cart(buyer, product)

    results = _concurrent_checkouts(
        scale_app, monkeypatch, buyers, coupon_code="LAST"
    )

    assert sorted(results.values()).count(201) == 1, results
    assert sorted(results.values()).count(400) == N - 1, results
    _db.session.expire_all()
    assert _db.session.get(Coupon, cid).used_count == 1
    assert CouponRedemption.query.filter_by(coupon_id=cid).count() == 1


def test_50_verifications_of_one_totp_code_admit_exactly_one(scale_app, monkeypatch):
    secret = pyotp.random_base32()
    user = _user()
    user.two_factor_enabled = True
    user.two_factor_method = TOTP_METHOD
    user.verification_method = None
    user.two_factor_totp_secret = two_factor_service.encrypt_totp_secret(
        secret
    )
    _db.session.commit()
    uid = user.id
    code = pyotp.TOTP(secret).now()

    tokens = [pyotp.random_base32() for _ in range(N)]
    for raw in tokens:
        _db.session.add(
            TwoFactorChallenge(
                user_id=uid,
                token_hash=two_factor_service._token_hash(raw),
                purpose=SECURITY_PURPOSE,
                method=TOTP_METHOD,
                expires_at=datetime.utcnow() + timedelta(minutes=10),
            )
        )
    _db.session.commit()

    real = two_factor_service._matching_totp_counter
    gate = _barrier(N)

    def synced(*a, **k):
        out = real(*a, **k)
        _wait(gate)
        return out

    monkeypatch.setattr(
        two_factor_service, "_matching_totp_counter", synced
    )

    results = {}

    def do(i):
        with scale_app.app_context():
            user_i = _db.session.get(User, uid)
            try:
                two_factor_service.verify_security_challenge(
                    user_i, tokens[i], code
                )
                results[i] = "ok"
            except Exception as exc:  # noqa: BLE001 - outcome is the data
                results[i] = type(exc).__name__

    _run(N, do)

    accepted = [k for k, v in results.items() if v == "ok"]
    assert len(accepted) == 1, results
    _db.session.expire_all()
    assert (
        _db.session.get(User, uid).two_factor_last_totp_counter is not None
    )


# --------------------------------------------------------------------------- #
# 2. Races with no prior coverage
# --------------------------------------------------------------------------- #

def test_50_reviews_on_one_product_leave_a_consistent_aggregate(scale_app):
    """rating_avg / rating_count are recomputed, not incremented (ADR 0015).

    Recompute is the safe shape only if every writer sees every prior
    commit. This measures whether that holds at 50.
    """
    store = _store()
    product = _product(store, stock=N)
    pid = product.id

    reviewers = [_user(email=f"rev-{i}@scale.local") for i in range(N)]
    for reviewer in reviewers:
        _delivered_order(reviewer, product)
    order_by_user = {
        o.user_id: o.id for o in Order.query.filter_by(store_id=store.id)
    }
    headers = [_token(scale_app, c) for c in reviewers]
    ratings = [(i % 5) + 1 for i in range(N)]

    gate = _barrier(N)
    results = {}

    def do(i):
        _wait(gate)
        results[i] = scale_app.test_client().post(
            "/api/reviews",
            json={
                "product_id": pid,
                "order_id": order_by_user[reviewers[i].id],
                "rating": ratings[i],
                "title": "t",
                "body": "body text",
            },
            headers=headers[i],
        ).status_code

    _run(N, do)

    created = sum(1 for c in results.values() if c == 201)
    _db.session.expire_all()
    product = _db.session.get(Product, pid)
    rows = Review.query.filter_by(product_id=pid).count()

    assert product.rating_count == rows, (
        f"stored rating_count={product.rating_count} but {rows} review rows "
        f"exist ({created} POSTs returned 201): lost update on the "
        f"denormalised aggregate. results={results}"
    )
    assert product.rating_count == created


def test_50_stores_with_the_same_name_all_succeed(scale_app):
    """Store.name has no unique constraint and there is no slug. Nothing is
    contended, so nothing is a race — 50 identical names all persist.
    """
    owners = [_user("vendor", email=f"v-{i}@scale.local") for i in range(N)]
    headers = [_token(scale_app, o) for o in owners]
    gate = _barrier(N)
    results = {}

    def do(i):
        _wait(gate)
        results[i] = scale_app.test_client().post(
            "/api/stores",
            json={
                "name": "Hamra Grocery",
                "description": "d",
                "location": "Beirut",
                "contact_info": "s@scale.local",
                "inside_city_delivery_fee": 1,
                "outside_city_delivery_fee": 2,
            },
            headers=headers[i],
        ).status_code

    _run(N, do)

    assert sorted(results.values()).count(201) == N, results
    assert Store.query.filter_by(name="Hamra Grocery").count() == N


def test_50_redemptions_by_one_customer_of_a_per_user_limit_1_coupon(scale_app):
    """The per-user cap has no counter column — it is a row count taken
    after the coupons-row UPDATE inside the same transaction. Measures
    whether that serialisation point holds one customer to one use at 50.

    Service level, not HTTP: one customer has exactly one cart, so 50
    concurrent checkouts would fail 49 on 'empty cart', not on the cap.
    """
    store = _store()
    coupon = Coupon(
        code="ONCE", discount_type="fixed", value=5, per_user_limit=1,
        is_active=True, store_id=store.id,
    )
    customer = _user()
    _db.session.add(coupon)
    _db.session.commit()
    cid, uid, sid = coupon.id, customer.id, store.id

    gate = _barrier(N)
    results = {}

    def do(i):
        with scale_app.app_context():
            session = _db.session
            _wait(gate)
            try:
                coupon_i = session.get(Coupon, cid)
                order = Order(
                    user_id=uid, store_id=sid, status="pending",
                    delivery_address="x", delivery_city="Beirut",
                    total_price=1,
                )
                session.add(order)
                session.flush()
                coupon_service.claim(coupon_i, uid)
                coupon_service.record(coupon_i, uid, order.id, 5)
                session.commit()
                results[i] = "ok"
            except Exception as exc:  # noqa: BLE001
                session.rollback()
                results[i] = type(exc).__name__

    _run(N, do)

    ok = [k for k, v in results.items() if v == "ok"]
    _db.session.expire_all()
    assert len(ok) == 1, results
    assert CouponRedemption.query.filter_by(
        coupon_id=cid, user_id=uid
    ).count() == 1
    assert _db.session.get(Coupon, cid).used_count == 1


def test_50_wrong_codes_are_all_counted(scale_app, monkeypatch):
    """Every simultaneous wrong guess is counted exactly once.

    ``attempt_count`` was ``+= 1`` in Python: fifty guesses arriving
    together all read the same old value and all wrote old+1, so most of
    the attempts vanished and the max-attempts lock never tripped. The
    increment is now a conditional UPDATE, so the count is exact however
    many arrive at once — the same guard the stock decrement uses.
    """
    user = _user()
    uid = user.id
    raw = "resend-attempts-token"

    _db.session.add(
        TwoFactorChallenge(
            user_id=uid,
            token_hash=two_factor_service._token_hash(raw),
            purpose=two_factor_service.REGISTRATION_PURPOSE,
            method="email",
            code_hash=generate_password_hash("000000", method=_FAST_HASH),
            expires_at=datetime.utcnow() + timedelta(minutes=10),
            send_count=1,
        )
    )
    _db.session.commit()

    gate = _barrier(N)

    def always_wrong(*_a, **_k):
        _wait(gate)
        return False

    monkeypatch.setattr(
        two_factor_service, "_verify_challenge_code", always_wrong
    )

    def do(_i):
        with scale_app.app_context():
            try:
                two_factor_service.verify_registration_challenge(
                    raw, "999999"
                )
            except Exception:  # noqa: BLE001 - the failure is the point
                pass

    _run(N, do)

    _db.session.expire_all()
    challenge = TwoFactorChallenge.query.filter_by(user_id=uid).one()
    assert challenge.attempt_count == N, (
        f"{N - challenge.attempt_count} attempts were lost to the race"
    )
    assert challenge.consumed_at is not None, "the challenge should be locked"


def _resend_challenge(uid, raw, send_count=1, last_sent_ago=timedelta(hours=1)):
    _db.session.add(
        TwoFactorChallenge(
            user_id=uid,
            token_hash=two_factor_service._token_hash(raw),
            purpose=two_factor_service.REGISTRATION_PURPOSE,
            method="email",
            code_hash=generate_password_hash("000000", method=_FAST_HASH),
            expires_at=datetime.utcnow() + timedelta(minutes=10),
            send_count=send_count,
            last_sent_at=datetime.utcnow() - last_sent_ago,
        )
    )
    _db.session.commit()


def _race_resends(scale_app, monkeypatch, raw):
    """Fire N resends of one challenge, all released together."""
    sent = []
    gate = _barrier(N)

    def counting_send(*_a, **_k):
        sent.append(1)

    def synced_code():
        _wait(gate)
        return "123456"

    monkeypatch.setattr(
        two_factor_service, "_send_verification_code", counting_send
    )
    monkeypatch.setattr(
        two_factor_service, "_generate_verification_code", synced_code
    )

    outcomes = []

    def do(_i):
        with scale_app.app_context():
            try:
                two_factor_service.resend_registration_code(raw)
                outcomes.append("sent")
            except Exception as exc:  # noqa: BLE001 - outcome is the data
                outcomes.append(type(exc).__name__)

    _run(N, do)
    return outcomes, sent


def test_50_simultaneous_resends_send_one_email(scale_app, monkeypatch):
    """The resend cooldown holds when every request arrives at once.

    The cooldown was read-then-written: fifty resends fired together all
    read the same old ``last_sent_at``, all decided the window had passed,
    and all sent. One request per cooldown is the whole point of the
    control, so that is fifty emails from a guard meant to allow one.
    The window is now re-tested inside the claiming UPDATE.
    """
    user = _user()
    uid = user.id
    raw = "cooldown-race-token"
    _resend_challenge(uid, raw)

    outcomes, sent = _race_resends(scale_app, monkeypatch, raw)

    assert outcomes.count("sent") == 1, outcomes.count("sent")
    assert len(sent) == 1, f"{len(sent)} emails escaped a one-per-cooldown gate"

    _db.session.expire_all()
    challenge = TwoFactorChallenge.query.filter_by(user_id=uid).one()
    assert challenge.send_count == 2


def test_50_simultaneous_resends_respect_the_send_limit(
    scale_app, monkeypatch
):
    """With the cooldown out of the way, the send cap is still exact.

    A negative cooldown makes that guard always pass, so the only thing
    left holding the line is ``send_count < TWO_FACTOR_MAX_EMAIL_SENDS``
    -- which is the condition being tested. Read-then-write let all fifty
    through; as a WHERE clause it admits exactly the remaining allowance.
    """
    monkeypatch.setitem(
        scale_app.config, "TWO_FACTOR_EMAIL_RESEND_COOLDOWN_SECONDS", -1
    )
    limit = scale_app.config["TWO_FACTOR_MAX_EMAIL_SENDS"]

    user = _user()
    uid = user.id
    raw = "send-limit-race-token"
    _resend_challenge(uid, raw, send_count=1)

    outcomes, sent = _race_resends(scale_app, monkeypatch, raw)

    remaining = limit - 1  # the challenge was created having sent one
    assert outcomes.count("sent") == remaining, outcomes.count("sent")
    assert len(sent) == remaining, f"{len(sent)} emails for a {limit} cap"

    _db.session.expire_all()
    challenge = TwoFactorChallenge.query.filter_by(user_id=uid).one()
    assert challenge.send_count == limit
