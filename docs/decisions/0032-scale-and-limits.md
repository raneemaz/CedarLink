# 0032 — Scale and limits

**Date:** 2026-09-07
**Status:** accepted

Numbered 0032, not 0031 as the prompt asked: `0031-privacy-policy-and-terms.md`
already exists on `main`.

This session **measured**. Nothing here is fixed. A defect found by a
measurement is a result, and two of them are recorded below as work for
later sessions.

Reproduce:

```
pytest tests/integration/test_scale_concurrency.py   # part 1
python scripts/measure_scale.py                       # part 2  -> _scale-measurements.md
python scripts/loadtest.py                            # part 3  -> _loadtest-results.md
```

The demo seed and `instance/cedarlink.db` are never touched — every script
builds a throwaway database.

---

## Part 1 — the concurrency guards at 50 threads

`tests/integration/test_scale_concurrency.py`. Each worker is held at a
`threading.Barrier` the instant it has read what it needs and before it
writes, then all are released together. The app is built with a
64-connection pool so 50 really is 50 (the default 15-connection ceiling
is measured in part 3).

| race | at 2–3 threads | at 50 | result |
|---|---|---|---|
| last unit of stock | 1 of 2 | **1 of 50** | holds |
| 25 units, 50 buyers | — | **25 of 50** | holds |
| coupon `usage_limit = 1` | 1 of 2 | **1 of 50** (49 × HTTP 400) | holds |
| TOTP replay counter | 1 of 2 | **1 of 50** | holds |
| 50 reviews → one product's `rating_avg`/`rating_count` *(new)* | — | `rating_count == 50`, exact | holds **under SQLite** — see part 4 |
| 50 store creations, same name *(new)* | — | **50 of 50 succeed** | not a race — nothing is contended |
| `per_user_limit = 1`, one customer, 50× *(new)* | 1 of 2 | **1 of 50** | holds |

**No guard broke at 50.** Every `UPDATE ... WHERE <condition>` with a
rowcount-0 refusal admits exactly the right number no matter the
interleaving. The coupon-exhausted losers get HTTP 400 (the whole checkout
fails rather than silently dropping the discount) — same as the existing
2-thread test, by design.

Two observations that are not failures:

- **Store name has no unique constraint and there is no slug.** Nothing
  reads store identity except `/stores/:id`, so 50 identical `"Hamra
  Grocery"` rows is the correct outcome, not a lost race.
- **The `per_user_limit` cap has no counter column.** It is a `COUNT` of
  redemption rows taken *after* `claim()`'s `UPDATE coupons SET used_count
  = used_count + 1` in the same transaction. The `used_count` UPDATE is
  what serialises concurrent claimants on the coupon row; the loser then
  sees the winner's committed redemption and raises. It holds at 50, but
  it is subtler than a pure conditional UPDATE and depends on that write
  ordering.

---

## Part 2 — query cost at 10 vs 10,000 stores

`scripts/measure_scale.py`. Large database: **10,000 stores, 100,000
products, 50,000 orders, 100,000 order items**, seeded in ~5 s. Baseline:
10 stores, 100 products, 50 orders. Wall time is best-of-3; query count is
every statement the request issued. Full plans in
[`_scale-measurements.md`](_scale-measurements.md).

| endpoint | queries (10 → 10k) | wall ms (10 → 10k) |
|---|---|---|
| store directory + `is_open_now` | 3 → 3 | 5 → 8 |
| nearby search (Beirut) | 2 → 3 | 2 → **171** |
| product listing + category filter | 19 → 19 | 10 → 36 |
| product listing + `hide_out_of_stock` | 18 → 19 | 10 → 37 |
| vendor dashboard, 90 days | 10 → 10 | 10 → **161** |
| admin overview | 13 → 13 | 8 → **144** |

**Query counts are flat.** There is no unbounded N+1 anywhere — the growth
is entirely in per-statement scan cost. Indexes actually present on the
hot tables (confirmed against `migrations/versions/`):

- `stores`: `ix_stores_lat_lng` only
- `products`: **none**
- `orders`: **none**
- `order_items`: **none**
- `reviews`: product / store / user, plus the two uniques
- `coupon_redemptions`: `(coupon_id, user_id)`

### Findings (named, not fixed)

**F1 — `orders` and `order_items` carry no secondary index.** Every
analytics query is `SCAN orders WHERE store_id = ? AND created_at BETWEEN
? AND ?` — a full scan of all 50,000 orders, six times per dashboard load.
The goods and discount figures additionally `SCAN order_items` (100,000
rows) and join. `stores.owner_id` is also unindexed, so resolving the
caller's own store is another `SCAN stores`. Result: the vendor dashboard
is **16× slower** at 50k orders and grows linearly from here. Schema
problem — follows to any database.

**F2 — the product-card serializer is a per-row N+1.** `product_card()`
touches `product.images` and `product.store` with no eager load, so a page
of 10 fires ~17 extra statements. Each images lookup is itself a `SCAN
product_images` (no index on `product_images.product_id`). Bounded by page
size, so the wall-time hit is small today (36 ms), but it is a query per
row and the images scan grows with that table. Schema + code problem —
follows to any database, and is *worse* over a network round trip.

**F3 — `paginate()` count.** Every listing issues `SELECT count(*)` over
the full filtered join — a second `SCAN products` of all 100,000 rows. The
keyword branch makes it a six-column `ILIKE` scan. O(rows) everywhere;
Postgres needs `pg_trgm` for the keyword case.

**F4 — `nearby()` hydrates the whole bounding box.** `ix_stores_lat_lng`
range-scans latitude only (leading column of the composite); longitude is
a residual filter. Every store in the latitude band is loaded as an ORM
object, its `hours` selectin-loaded, and haversine-filtered in Python
*before* the page of 10 is taken. O(stores in band), not O(page). The
"no native spatial index" part is SQLite-shaped; the "materialise
everything then paginate in Python" part follows to any database.

**F5 — admin overview is 13 sequential full-table aggregates.** Five are
filtered `COUNT(*)` over all 10,000 stores that could be one `GROUP BY`.
Not an N+1; O(total rows) with a large constant. Same shape on Postgres,
which counts faster and can use partial indexes.

**F6 — store directory sort.** `ORDER BY stores.name` with no index →
`SCAN stores | USE TEMP B-TREE FOR ORDER BY` on every request, plus a
second `SCAN stores` for the count. Only 8 ms at 10k absolute rows, but
O(stores).

Not a problem: `is_open_now` in the directory is **not** an N+1 — the
`selectinload(Store.hours)` from CL-18 holds it to one extra query for the
whole page, at 10 stores and at 10,000.

---

## Part 3 — real concurrency against the running app

`scripts/loadtest.py`, demo seed copied to a throwaway file, app
in-process with the **default** pool (QueuePool 5 + 10 = 15) and SQLite's
default 5 s busy timeout, rollback journal (not WAL). Full table in
[`_loadtest-results.md`](_loadtest-results.md).

| path | N = 10 | N = 50 | N = 100 |
|---|---|---|---|
| `GET /api/products` | 100% ok, ~46 req/s | 100% ok, ~50 req/s | 100% ok, ~50 req/s |
| `POST /api/orders` (checkout) | 100% ok, ~10 req/s | 100% ok, ~12 req/s | **95–100% ok, 0–5 × HTTP 500** (6 runs: 0,1,2,2,3,5) |

- **Reads are flat at ~50 req/s** from 10 to 100 clients — they neither
  scale up (GIL + 15-connection pool + in-process harness) nor degrade
  (SQLite readers do not block readers). Zero errors at any N.
- **Writes are flat at ~12–13 orders/sec** regardless of concurrency —
  SQLite serialises every checkout transaction through the one write lock.
- **First failure: checkout at N ≈ 100.** Intermittent — across six runs,
  0 to 5 of 100 requests returned the sanitised HTTP 500 (correlation id,
  no SQL leaked). The recorded server-side cause is always:

  ```
  sqlite3.OperationalError: database is locked
  [SQL: INSERT INTO orders (user_id, store_id, status, delivery_address, ...)]
  ```

  At ~100 concurrent write transactions the contention on the
  database-level write lock exceeds the 5-second busy timeout for an
  unlucky few. **N = 50 was clean on every run.** The failure is a
  timeout, not a deadlock: it is the tail of the queue, and it moves with
  scheduling.

---

## Part 4 — the binding constraint, and which findings port

### SQLite's single-writer model is the ceiling

One writer at a time, whole-database lock under the rollback journal.
Reads are concurrent and fine. Writes are a single queue: the measured
checkout ceiling is **~12/sec**, and past roughly 50 concurrent writers
the 5 s busy timeout starts turning contention into `database is locked`
500s (0–5% at N=100, N=50 clean).

### Ports to Postgres unchanged — the correctness patterns

- **The conditional-UPDATE guard** — stock decrement, coupon
  `usage_limit`, the TOTP replay counter — is `UPDATE … WHERE <condition>`
  with `rowcount == 0` as the refusal. This is ordinary SQL. The database
  picks one winner atomically; nothing about it is SQLite-specific.
  Verified at 50 threads here, and Postgres behaves identically (the row
  lock serialises updaters, each re-checks the condition). **This pattern
  does not change when the database does.**
- **The per-user coupon cap** (count-after-UPDATE in one transaction)
  leans on the `used_count` UPDATE as a row-level serialisation point.
  Postgres takes that same row lock, so it ports — noted as subtle above.

### SQLite-specific — Postgres resolves these

- **`database is locked` under concurrent checkout.** Postgres has
  row-level locking and MVCC: two checkouts touching different products,
  coupons and orders never block each other; only a true row conflict
  serialises. The ~12/sec write ceiling and the N=100 500s are SQLite
  artefacts. WAL mode plus a larger `busy_timeout` would soften them on
  SQLite without removing the single-writer ceiling.
- **The flat ~50 req/s read result** is connection-pool plus GIL plus the
  in-process harness, not a database limit. A real deployment (several
  gunicorn workers, Postgres) scales reads out.

### Would follow the app to Postgres — the schema and query findings

None of these are fixed here; this is the list a later session works from.

- **Missing indexes** (F1): `orders(store_id)`, `orders(created_at)` (or a
  composite), `order_items(order_id)`, `products(store_id)`,
  `products(category_id)`, `product_images(product_id)`,
  `stores(owner_id)`. Postgres does not auto-index foreign keys either;
  the vendor dashboard and admin overview still degrade with row count,
  from a lower baseline.
- **The `product_card` N+1** (F2). A lazy load is a round trip on any
  database, and worse across a network. The fix is `selectinload` /
  `joinedload` on the listing query.
- **`paginate()`'s `COUNT(*)` and the keyword `ILIKE`** (F3) — O(rows)
  everywhere; Postgres needs `pg_trgm` for the keyword scan.
- **`nearby()` materialising the whole bounding box** (F4) before
  paginating in Python.
- **The review-aggregate recompute is the one race SQLite is hiding.**
  `review_service._recalculate_rating` does an unlocked `SELECT avg(),
  count()` and then a separate `UPDATE products SET rating_avg =, rating_count =`.
  SQLite serialises writers, so every recompute sees all prior commits and
  the aggregate is exact at 50 (the test passes). **Under Postgres READ
  COMMITTED, two concurrent reviewers can both read the pre-commit count,
  both write, and the second write stores a stale, too-low
  `rating_count`.** ADR 0015 calls recompute "the safe shape" — it is safe
  against the lost-update *arithmetic*, but not against a concurrent
  overwrite of the denormalised column on an MVCC database. The fix, when
  it is time: `SELECT … FOR UPDATE` on the product row, or fold the
  aggregate into an atomic statement, or move it to a trigger. Not shipped
  here, per the brief.

### Not a defect

Store-name collisions (part 1). No unique constraint, no slug, nothing
depends on one.

---

## Consequences

- `tests/integration/test_scale_concurrency.py` — 7 tests, part of the
  suite, ~27 s. They assert the invariants, not timings, so they are not
  flaky.
- `scripts/measure_scale.py` and `scripts/loadtest.py` — re-runnable,
  write their `_*.md` companions next to this file.
- Findings F1–F6 and the review-aggregate race are logged here as the
  scale backlog. The conditional-UPDATE correctness work needs no change.
- No production code changed in this session.
