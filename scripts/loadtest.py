"""Concurrency load test against the app on the demo seed.

Copies ``instance/cedarlink.db`` to a throwaway file (the demo seed is
never mutated), pads it with enough customers/carts to drive the writes,
then hammers two paths at 10, 50 and 100 simultaneous clients:

  * read:     GET /api/products?limit=20   (public)
  * checkout: POST /api/orders             (one distinct customer each)

The app runs in-process with its **default** connection pool (QueuePool,
size 5 + overflow 10 = 15) and SQLite's default 5 s busy timeout — this is
the ceiling a single gunicorn worker actually has. Reports throughput,
error rate, and the first exception's real message.

    python scripts/loadtest.py
"""

import logging
import shutil
import sys
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

logging.disable(logging.CRITICAL)  # the tracebacks are captured, not printed

from flask_jwt_extended import create_access_token  # noqa: E402
from werkzeug.security import generate_password_hash  # noqa: E402

import app.utils.errors as _errors  # noqa: E402
from app import create_app  # noqa: E402
from app.config import DevConfig  # noqa: E402
from app.extensions import db  # noqa: E402
from app.models.cart import Cart  # noqa: E402
from app.models.cart_item import CartItem  # noqa: E402
from app.models.product import Product  # noqa: E402
from app.models.store import Store  # noqa: E402
from app.models.user import User  # noqa: E402

SERVER_EXCEPTIONS = []

# Routes catch their own exception and return a sanitised 500 with a
# correlation id, so the real cause never reaches a Flask signal. It does
# pass through log_and_correlate; wrap that to record the true message.
_real_log_and_correlate = _errors.log_and_correlate


def _capture(exc, context):
    SERVER_EXCEPTIONS.append(f"{type(exc).__name__}: {exc}")
    return _real_log_and_correlate(exc, context)


_errors.log_and_correlate = _capture
_errors.internal_error.__globals__["log_and_correlate"] = _capture

ROOT = Path(__file__).resolve().parents[1]
SRC_DB = ROOT / "instance" / "cedarlink.db"
WORK_DB = ROOT / "_loadtest.db"
LEVELS = (10, 50, 100)
CLIENTS = 170


def _prepare(app):
    """Add CLIENTS throwaway customers, each with one unit of a
    high-stock product already in their cart."""
    with app.app_context():
        store = Store.query.filter(Store.is_visible).first()
        # Throwaway copy: let the busy store take orders round the clock so
        # the test measures concurrency, not the shop's opening hours.
        store.accepts_orders_when_closed = True
        store.override_status = None
        store.override_until = None
        product = Product(
            name_en="Load Test Widget",
            description_en="x",
            price=5,
            stock=10_000_000,
            store_id=store.id,
            category_id=Product.query.first().category_id,
        )
        db.session.add(product)
        db.session.flush()

        ids = []
        pw = generate_password_hash("pw", method="pbkdf2:sha256:1")
        for i in range(CLIENTS):
            user = User(
                first_name="Load", last_name="Test",
                email=f"load{i}@loadtest.local", password=pw,
                phone=f"+96170{i:06d}", role="customer", is_verified=True,
                verification_method="email",
            )
            db.session.add(user)
            db.session.flush()
            cart = Cart(user_id=user.id)
            db.session.add(cart)
            db.session.flush()
            db.session.add(
                CartItem(cart_id=cart.id, product_id=product.id, quantity=1)
            )
            ids.append(user.id)
        db.session.commit()

        tokens = []
        for uid in ids:
            tokens.append(
                "Bearer " + create_access_token(
                    identity=str(uid), additional_claims={"role": "customer"}
                )
            )
        return tokens


def _fire(app, level, make_request):
    """Run ``make_request(i)`` on ``level`` threads at once. Returns
    (throughput_per_s, error_rate, first_error_repr)."""
    results = []
    errors = []

    def one(i):
        start = time.perf_counter()
        try:
            status, body = make_request(i)
            ok = status < 400
            if not ok:
                errors.append(f"HTTP {status} {body}")
            return ok, time.perf_counter() - start
        except Exception as exc:  # noqa: BLE001
            errors.append(f"{type(exc).__name__}: {exc}")
            return False, time.perf_counter() - start

    wall_start = time.perf_counter()
    with ThreadPoolExecutor(max_workers=level) as pool:
        futures = [pool.submit(one, i) for i in range(level)]
        for future in as_completed(futures):
            results.append(future.result())
    wall = time.perf_counter() - wall_start

    ok_count = sum(1 for ok, _ in results if ok)
    err_count = len(results) - ok_count
    first_error = (
        SERVER_EXCEPTIONS[0] if SERVER_EXCEPTIONS
        else (errors[0] if errors else "-")
    )
    SERVER_EXCEPTIONS.clear()
    return {
        "n": level,
        "wall_s": round(wall, 2),
        "throughput": round(len(results) / wall, 1),
        "ok": ok_count,
        "errors": err_count,
        "error_rate": round(100 * err_count / len(results), 1),
        "first_error": " ".join(first_error.split())[:200],
    }


def main():
    if not SRC_DB.exists():
        sys.exit(f"no demo db at {SRC_DB} — run `flask seed` first")
    if WORK_DB.exists():
        WORK_DB.unlink()
    shutil.copy(SRC_DB, WORK_DB)

    class Cfg(DevConfig):
        SQLALCHEMY_DATABASE_URI = f"sqlite:///{WORK_DB.as_posix()}"
        RATELIMIT_ENABLED = False

    app = create_app(Cfg)
    tokens = _prepare(app)

    print("pool: QueuePool size 5 + overflow 10 = 15 connections\n")

    rows = []
    for level in LEVELS:
        def read_request(i, _app=app):
            resp = _app.test_client().get("/api/products?limit=20")
            return resp.status_code, ""

        rows.append(("read  GET /api/products",
                     _fire(app, level, read_request)))

    for level in LEVELS:
        # A fresh slice of customers per level so a cart is only spent once.
        base = {10: 0, 50: 10, 100: 60}[level]  # non-overlapping slices

        def checkout_request(i, _app=app, _base=base):
            resp = _app.test_client().post(
                "/api/orders",
                json={
                    "delivery_address": "1 Load St",
                    "delivery_city": "Beirut",
                    "payment_method": "cash_on_delivery",
                },
                headers={"Authorization": tokens[_base + i]},
            )
            return resp.status_code, (resp.get_data(as_text=True) or "")[:120]

        rows.append(("checkout POST /api/orders",
                     _fire(app, level, checkout_request)))

    print(f"{'path':28} {'N':>4} {'wall_s':>7} {'req/s':>7} "
          f"{'ok':>4} {'err':>4} {'err%':>6}  first_error")
    for label, r in rows:
        print(f"{label:28} {r['n']:>4} {r['wall_s']:>7} {r['throughput']:>7} "
              f"{r['ok']:>4} {r['errors']:>4} {r['error_rate']:>6}  "
              f"{r['first_error']}")

    lines = ["# Load test (generated by scripts/loadtest.py)\n",
             "Default pool (15 connections), SQLite 5 s busy timeout, "
             "app in-process.\n",
             "| path | N | wall (s) | req/s | ok | err | err % | first error |",
             "|---|--:|--:|--:|--:|--:|--:|---|"]
    for label, r in rows:
        lines.append(
            f"| {label} | {r['n']} | {r['wall_s']} | {r['throughput']} | "
            f"{r['ok']} | {r['errors']} | {r['error_rate']} | "
            f"`{r['first_error']}` |"
        )
    dest = ROOT / "docs" / "decisions" / "_loadtest-results.md"
    dest.write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(f"\nwritten to {dest}")

    with app.app_context():
        db.engine.dispose()
    try:
        WORK_DB.unlink(missing_ok=True)
    except OSError:
        pass  # Windows may still hold the handle; *.db is gitignored


if __name__ == "__main__":
    main()
