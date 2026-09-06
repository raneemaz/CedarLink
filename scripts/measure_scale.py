"""Measure CedarLink's read-path query plans and cost at two data sizes.

Throwaway databases only — the demo seed and ``cedarlink.db`` are never
touched. Builds a small database (10 stores) and a large one (10,000
stores / 100,000 products / 50,000 orders), then runs five endpoints
against each, recording:

  * the number of SQL statements the request issued
  * ``EXPLAIN QUERY PLAN`` for every distinct SELECT
  * wall-clock time (best of 3)

Anything whose statement count or wall time grows with the row count is an
N+1 or a missing index. This script names them; it does not fix them.

    python scripts/measure_scale.py

Writes a Markdown table to stdout and to
``docs/decisions/_scale-measurements.md`` for the ADR to quote.
"""


import random

import sys
import time
from datetime import datetime, time as dtime, timedelta, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from sqlalchemy import event, insert, text  # noqa: E402

from app import create_app  # noqa: E402
from app.config import TestConfig  # noqa: E402
from app.extensions import db  # noqa: E402
from app.models.category import Category  # noqa: E402
from app.models.order import Order  # noqa: E402
from app.models.order_item import OrderItem  # noqa: E402
from app.models.product import Product  # noqa: E402
from app.models.store import Store  # noqa: E402
from app.models.store_hours import StoreHours  # noqa: E402
from app.models.user import User  # noqa: E402
from flask_jwt_extended import create_access_token  # noqa: E402
from werkzeug.security import generate_password_hash  # noqa: E402

random.seed(1)

BEIRUT_LAT, BEIRUT_LNG = 33.8938, 35.5018
PASSWORD_HASH = generate_password_hash("pw", method="pbkdf2:sha256:1")
NOW = datetime.now(timezone.utc).replace(tzinfo=None)

SCALES = {
    "small": dict(stores=10, products_per_store=10, orders=50),
    "large": dict(stores=10_000, products_per_store=10, orders=50_000),
}


# --------------------------------------------------------------------------- #
# Seeding — raw bulk inserts, one transaction, sync off. No ORM per row.
# --------------------------------------------------------------------------- #

def _seed(scale):
    cfg = SCALES[scale]
    n_stores = cfg["stores"]
    n_products = n_stores * cfg["products_per_store"]
    n_orders = cfg["orders"]

    db.session.execute(text("PRAGMA synchronous=OFF"))
    db.session.execute(text("PRAGMA journal_mode=MEMORY"))

    cats = [
        {"name_en": f"Category {i}", "description": "c"} for i in range(10)
    ]
    db.session.execute(insert(Category.__table__), cats)
    cat_ids = [row[0] for row in db.session.execute(
        text("SELECT id FROM categories")
    )]

    # Users: one vendor per store, plus 2000 customers and one admin.
    n_customers = min(2000, max(50, n_orders // 20))
    users = []
    for i in range(n_stores):
        users.append({
            "first_name": "V", "last_name": "endor",
            "email": f"vendor{i}@scale.local", "password": PASSWORD_HASH,
            "phone": f"+9611{i:07d}", "role": "vendor", "is_verified": True,
            "verification_method": "email", "language": "en",
            "currency": "USD", "theme": "system", "is_active": True,
            "two_factor_enabled": False,
        })
    for i in range(n_customers):
        users.append({
            "first_name": "C", "last_name": "ustomer",
            "email": f"cust{i}@scale.local", "password": PASSWORD_HASH,
            "phone": f"+9612{i:07d}", "role": "customer", "is_verified": True,
            "verification_method": "email", "language": "en",
            "currency": "USD", "theme": "system", "is_active": True,
            "two_factor_enabled": False,
        })
    users.append({
        "first_name": "A", "last_name": "dmin", "email": "admin@scale.local",
        "password": PASSWORD_HASH, "phone": "+9613000", "role": "admin",
        "is_verified": True, "verification_method": "email", "language": "en",
        "currency": "USD", "theme": "system", "is_active": True,
        "two_factor_enabled": False,
    })
    _bulk(User.__table__, users)

    vendor_ids = [r[0] for r in db.session.execute(
        text("SELECT id FROM users WHERE role='vendor' ORDER BY id")
    )]
    customer_ids = [r[0] for r in db.session.execute(
        text("SELECT id FROM users WHERE role='customer' ORDER BY id")
    )]

    # Stores — 70% carry a Beirut-area pin, the rest have none.
    stores = []
    for i, owner_id in enumerate(vendor_ids):
        has_pin = i % 10 < 7
        stores.append({
            "owner_id": owner_id,
            "name": f"Store {i}",
            "description": "d",
            "location": random.choice(["Beirut", "Tripoli", "Saida"]),
            "contact_info": "s@scale.local",
            "is_active": True,
            "inside_city_delivery_fee": 2, "outside_city_delivery_fee": 5,
            "delivery_available": True,
            "approval_status": "approved",
            "accepts_orders_when_closed": False,
            "rating_count": 0,
            "is_online_only": False,
            "latitude": (
                round(BEIRUT_LAT + random.uniform(-0.15, 0.15), 6)
                if has_pin else None
            ),
            "longitude": (
                round(BEIRUT_LNG + random.uniform(-0.15, 0.15), 6)
                if has_pin else None
            ),
        })
    _bulk(Store.__table__, stores)
    store_ids = [r[0] for r in db.session.execute(
        text("SELECT id FROM stores ORDER BY id")
    )]

    # Store hours — a 24/7 week for every store, so is_open_now has rows to
    # walk (it is called for every row in the directory).
    hours = []
    for sid in store_ids:
        for day in range(7):
            hours.append({
                "store_id": sid, "day_of_week": day,
                "opens_at": dtime(0, 0), "closes_at": dtime(0, 0),
            })
    _bulk(StoreHours.__table__, hours)

    # Products — 10 per store, ~15% out of stock.
    products = []
    for sid in store_ids:
        for j in range(cfg["products_per_store"]):
            products.append({
                "name_en": f"Product {sid}-{j}",
                "description_en": "d",
                "price": round(random.uniform(1, 200), 2),
                "stock": 0 if random.random() < 0.15 else random.randint(1, 50),
                "rating_count": 0,
                "store_id": sid,
                "category_id": random.choice(cat_ids),
                "created_at": NOW - timedelta(days=random.randint(0, 300)),
            })
    _bulk(Product.__table__, products)
    product_rows = list(db.session.execute(
        text("SELECT id, store_id, price FROM products ORDER BY id")
    ))
    by_store = {}
    for pid, sid, price in product_rows:
        by_store.setdefault(sid, []).append((pid, price))

    # Orders — spread over 180 days so a 90-day window covers about half.
    # Store 1 is the "busy" store used for the vendor-dashboard measurement.
    busy_store = store_ids[0]
    statuses = ["pending", "processing", "delivered", "delivered",
                "delivered", "canceled"]
    orders = []
    for i in range(n_orders):
        sid = busy_store if i % 5 == 0 else random.choice(store_ids)
        created = NOW - timedelta(
            days=random.randint(0, 180),
            seconds=random.randint(0, 86_400),
        )
        orders.append({
            "user_id": random.choice(customer_ids),
            "store_id": sid,
            "status": random.choice(statuses),
            "delivery_address": "1 Scale St",
            "delivery_city": "Beirut",
            "total_price": round(random.uniform(5, 400), 2),
            "delivery_fee": 2,
            "created_at": created,
            "updated_at": created,
        })
    _bulk(Order.__table__, orders)
    order_rows = list(db.session.execute(
        text("SELECT id, store_id FROM orders ORDER BY id")
    ))

    items = []
    for oid, sid in order_rows:
        picks = by_store.get(sid) or product_rows[:1]
        for pid, price in random.sample(picks, k=min(2, len(picks))):
            items.append({
                "order_id": oid, "product_id": pid,
                "quantity": random.randint(1, 3), "unit_price": price,
            })
    _bulk(OrderItem.__table__, items)

    db.session.commit()
    db.session.execute(text("ANALYZE"))
    db.session.commit()

    return dict(
        n_stores=n_stores, n_products=n_products, n_orders=n_orders,
        n_order_items=len(items),
        busy_store_id=busy_store,
        busy_vendor_id=stores[0]["owner_id"],
        a_category=cat_ids[0],
        admin_id=db.session.execute(
            text("SELECT id FROM users WHERE role='admin'")
        ).scalar(),
    )


def _bulk(table, rows, chunk=5000):
    for start in range(0, len(rows), chunk):
        db.session.execute(insert(table), rows[start:start + chunk])


# --------------------------------------------------------------------------- #
# Measurement
# --------------------------------------------------------------------------- #

class Recorder:
    def __init__(self):
        self.statements = []

    def __enter__(self):
        self.statements.clear()
        event.listen(db.engine, "before_cursor_execute", self._on)
        return self

    def __exit__(self, *exc):
        event.remove(db.engine, "before_cursor_execute", self._on)

    def _on(self, conn, cursor, statement, parameters, context, executemany):
        self.statements.append((statement, parameters))


def _plans(statements):
    seen = set()
    out = []
    for statement, params in statements:
        s = statement.strip()
        if not s.lower().startswith("select"):
            continue
        key = " ".join(s.split())
        if key in seen:
            continue
        seen.add(key)
        bind = params
        if isinstance(bind, (list, tuple)) and bind and isinstance(
            bind[0], (list, tuple, dict)
        ):
            bind = bind[0]
        try:
            raw = db.session.connection().connection.driver_connection
            cur = raw.cursor()
            cur.execute("EXPLAIN QUERY PLAN " + s, bind or [])
            rows = cur.fetchall()
            cur.close()
            detail = " | ".join(str(r[-1]) for r in rows)
        except Exception as exc:  # noqa: BLE001
            detail = f"(explain failed: {exc})"
        out.append(f"{detail}\n    {' '.join(s.split())[:240]}")
    return out


def _measure(client, method, path, headers=None, repeats=3):
    times = []
    statements = []
    for _ in range(repeats):
        rec = Recorder()
        start = time.perf_counter()
        with rec:
            resp = client.open(path, method=method, headers=headers or {})
        times.append(time.perf_counter() - start)
        statements = rec.statements
    return {
        "status": resp.status_code,
        "queries": len(statements),
        "ms": round(min(times) * 1000, 1),
        "plans": _plans(statements),
    }


def run(scale):
    db_path = Path(__file__).resolve().parents[1] / f"_scale_{scale}.db"
    if db_path.exists():
        db_path.unlink()

    class Cfg(TestConfig):
        SQLALCHEMY_DATABASE_URI = f"sqlite:///{db_path.as_posix()}"
        RATELIMIT_ENABLED = False

    app = create_app(Cfg)
    ctx = app.app_context()
    ctx.push()
    db.create_all()

    t0 = time.perf_counter()
    meta = _seed(scale)
    seed_s = time.perf_counter() - t0

    client = app.test_client()
    vendor_headers = {
        "Authorization": "Bearer " + create_access_token(
            identity=str(meta["busy_vendor_id"]),
            additional_claims={"role": "vendor"},
        )
    }
    admin_headers = {
        "Authorization": "Bearer " + create_access_token(
            identity=str(meta["admin_id"]),
            additional_claims={"role": "admin"},
        )
    }

    frm = (NOW - timedelta(days=90)).date().isoformat()
    to = NOW.date().isoformat()

    targets = {
        "store directory (+is_open_now)":
            ("GET", "/api/stores?limit=10", None),
        "nearby search (Beirut)":
            ("GET", f"/api/stores?near={BEIRUT_LAT},{BEIRUT_LNG}&radius=5",
             None),
        "product listing + category filter":
            ("GET", f"/api/products?category_id={meta['a_category']}&limit=10",
             None),
        "product listing + in_stock filter":
            ("GET",
             f"/api/products?category_id={meta['a_category']}"
             "&in_stock=true&limit=10", None),
        "vendor dashboard (90 days)":
            ("GET", f"/api/vendor/dashboard?from={frm}&to={to}",
             vendor_headers),
        "admin overview":
            ("GET", "/api/admin/reports", admin_headers),
    }

    results = {}
    for label, (method, path, headers) in targets.items():
        results[label] = _measure(client, method, path, headers)

    indexes = [
        (r[0], r[1])
        for r in db.session.execute(text(
            "SELECT tbl_name, name FROM sqlite_master WHERE type='index' "
            "AND tbl_name IN ('stores','products','orders','order_items',"
            "'reviews','users','coupon_redemptions') ORDER BY tbl_name, name"
        ))
    ]

    ctx.pop()
    return meta, seed_s, results, indexes


def main():
    out = []
    out.append("# Scale measurements (generated by scripts/measure_scale.py)\n")
    all_results = {}
    metas = {}
    indexes = []
    for scale in ("small", "large"):
        meta, seed_s, results, indexes = run(scale)
        metas[scale] = meta
        all_results[scale] = results
        out.append(
            f"\n## {scale}: {meta['n_stores']:,} stores, "
            f"{meta['n_products']:,} products, {meta['n_orders']:,} orders "
            f"({meta['n_order_items']:,} order items) — seeded in {seed_s:.1f}s\n"
        )
        out.append("| endpoint | queries | wall (ms) |")
        out.append("|---|---:|---:|")
        for label, r in results.items():
            out.append(f"| {label} | {r['queries']} | {r['ms']} |")

    out.append("\n## Query plans at large scale\n")
    for label, r in all_results["large"].items():
        out.append(f"\n### {label}  ·  {r['queries']} queries  ·  {r['ms']} ms")
        for plan in r["plans"]:
            out.append(f"\n```\n{plan}\n```")

    out.append("\n## Growth (small -> large)\n")
    out.append("| endpoint | queries s->l | ms s->l |")
    out.append("|---|---|---|")
    for label in all_results["small"]:
        s = all_results["small"][label]
        big = all_results["large"][label]
        out.append(
            f"| {label} | {s['queries']} -> {big['queries']} | "
            f"{s['ms']} -> {big['ms']} |"
        )

    out.append("\n## Indexes present on the hot tables (large db)\n")
    by_table = {}
    for tbl, name in indexes:
        by_table.setdefault(tbl, []).append(name)
    for tbl in ("users", "stores", "products", "orders", "order_items",
                "reviews", "coupon_redemptions"):
        out.append(f"- **{tbl}**: {', '.join(by_table.get(tbl, [])) or '(none)'}")

    report = "\n".join(out) + "\n"
    dest = Path(__file__).resolve().parents[1] / "docs" / "decisions" / \
        "_scale-measurements.md"
    dest.write_text(report, encoding="utf-8")
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass
    print(report)
    print(f"written to {dest}")


if __name__ == "__main__":
    main()
