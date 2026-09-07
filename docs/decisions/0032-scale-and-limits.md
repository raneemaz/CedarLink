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

### Findings (named)

> **F1, F2 and F6 were fixed in the follow-up pass — see Part 5.** F3, F4
> and F5 remain open. The original findings are kept verbatim below.

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
  artefacts. **The follow-up pass added a checkout retry (Part 5) — the
  N=100 500s are gone — and measured WAL: it roughly doubles throughput.**
  Neither removes the single-writer ceiling itself.
- **The flat ~50 req/s read result** is connection-pool plus GIL plus the
  in-process harness, not a database limit. A real deployment (several
  gunicorn workers, Postgres) scales reads out.

### Would follow the app to Postgres — the schema and query findings

This was the list a later session works from. **F1, F2, F6 and the
review-aggregate race are now done — Part 5.** What remains:

- **Missing indexes** (F1) — **done** (migration `bac2fb1331ba`, Part 5).
- **The `product_card` N+1** (F2) — **done** (`selectinload`, Part 5).
- **`paginate()`'s `COUNT(*)` and the keyword `ILIKE`** (F3) — O(rows)
  everywhere; Postgres needs `pg_trgm` for the keyword scan. Still open.
- **`nearby()` materialising the whole bounding box** (F4) before
  paginating in Python.
- **The review-aggregate recompute** — was "the one race SQLite is
  hiding": `review_service._recalculate_rating` did an unlocked `SELECT
  avg(), count()` then a separate `UPDATE`, which SQLite serialises but an
  MVCC database would let a concurrent writer overwrite with a stale
  count. **Done — Part 5.** It is now one atomic statement (the aggregate
  folded into the `UPDATE`), which is exactly the fix this bullet asked
  for. `tests/integration/test_rating_recompute_atomic.py`.

### Not a defect

Store-name collisions (part 1). No unique constraint, no slug, nothing
depends on one.

---

## Part 5 — follow-up pass, 2026-09-07 (with the security punch list, ADR 0033)

The scale backlog was measure-only. This pass fixes the parts that were
schema or code, and adds two measurements it had skipped. Migration
`bac2fb1331ba` (index-only, no data change, up/down/up clean,
`flask db check` agrees).

### F1 / F6 — the missing indexes, fixed

Added: `ix_orders_store_id_created_at` (composite — serves `store_id`
alone too), `ix_order_items_order_id`, `ix_products_store_id`,
`ix_products_category_id`, `ix_product_images_product_id`,
`ix_stores_owner_id`, `ix_stores_name`. `orders`, `order_items` and
`products` had **no** secondary index before.

`scripts/measure_scale.py`, same 10k / 100k / 50k throwaway seed, large
scale:

| endpoint | queries before → after | wall ms before → after |
|---|---|---|
| product listing + category filter | 19 → **4** | 43.6 → **~20** |
| store directory (+`is_open_now`) | 3 → 3 | 7.0 → **~5** |
| admin overview | 13 → 13 | 150.7 → **~110** |
| vendor dashboard (90 days) | 10 → 10 | 168.6 → **~290** ⚠ |

Every plan line that was `SCAN` is now `SEARCH … USING INDEX`. Three of
the four improve.

**The vendor dashboard regressed on this seed, and the reason is worth
recording.** S-2's seed gives store 1 **20% of all 50,000 orders**
(`i % 5 == 0`). At that selectivity SQLite's index-nested-loop join —
its *only* join strategy — is slower than the full scan + bloom-filter
hash it did before: ~5,000 in-window orders × index probes into
`order_items` × probes into `products`, versus one pass over 100,000
`order_items` rows. Re-run with a realistic 1% order share
(`i % 100`), the same query is **168.6 → 23 ms — a 7× win**. Postgres,
which has hash joins and a cost-based selectivity estimate, picks the
scan at 20% and the index at 1% and does not have this cliff. The indexes
stay: they are correct, required by `GET /api/vendor/orders` and the
admin top-stores join, and a real store's dashboard is <10 ms with them.

`tests/integration/test_product_listing_query_count.py` pins the F2 fix
(listing query count flat across page size, ≤ 5).

### F2 — the product-card N+1, fixed

`get_products` now `selectinload(Product.images, Product.store)` —
`product_card()` reads `product.images[0]` and `product.store.name` per
row. Page of 10: **19 → 4 queries** (main + count + one images batch +
one stores batch), regardless of page size.

### The review-aggregate recompute — now atomic (§4 above)

`review_service._recalculate_rating` is one
`UPDATE …/stores SET rating_count = (SELECT count()…), rating_avg =
(SELECT round(avg(),2)…) WHERE id = :id`. The unlocked-SELECT-then-write
shape that an MVCC database could lose an update on is gone.
`tests/integration/test_rating_recompute_atomic.py` asserts exactly one
statement per recompute. This ports to Postgres unchanged — which was the
whole point.

### `database is locked` on checkout — retried (part 3)

`app/utils/db_retry.with_write_retry`, checkout view only: on that error,
roll back, back off 50/100 ms, retry (3 attempts). `scripts/loadtest.py`
N=100 checkout, default pool: **before** 0,1,2,2,3,5 failures across 6
runs → **after** 0,0,0,0,0 across 5 runs. Throughput unchanged (~12/s) —
the retry costs only the unlucky few, and there are none now. The SQLite
single-writer ceiling itself is unchanged; the retry hides the tail, it
does not lift the wall.

### New measurement — WAL vs rollback journal

`scripts/loadtest.py --wal` (issues `PRAGMA journal_mode=WAL`; the app's
default is untouched). N=100, default pool, three runs each:

| path | rollback journal | WAL |
|---|---|---|
| `GET /api/products` @ 100 | ~55 req/s, 0 err | **~110 req/s**, 0 err |
| `POST /api/orders` @ 50 | ~13 req/s | **~24 req/s** |
| `POST /api/orders` @ 100 | ~13 req/s, 0 err (with retry) | **~28 req/s**, 0 err |

WAL roughly **doubles** read and write throughput and readers stop
blocking on the writer. This is a strong case for switching the default,
but that is a deployment decision (WAL needs a real filesystem, not a
network share; it leaves `-wal`/`-shm` sidecars) — recorded here, not
made.

### New measurement — `token_denylist` growth

`scripts/measure_denylist.py`. `GET /api/orders` (hits the JWT blocklist
loader), median of 400 requests, 0 vs 100,000 expired rows:

| rows | median ms | p99 ms |
|--:|--:|--:|
| 0 | 1.50 | 4.43 |
| 100,000 | 1.48 | 4.48 |

**No measurable cost.** The lookup is `SEARCH token_denylist USING
COVERING INDEX ix_token_denylist_jti` — O(log n). The missing cleanup job
is storage tidiness, not a per-request finding; a periodic
`DELETE … WHERE expires_at < now()` is roadmap (ADR 0033 §5b #11).

### Still open from the scale backlog

- **F3** — `paginate()`'s `COUNT(*)` over the filtered join, and the
  six-column keyword `ILIKE`, are still O(rows). Postgres needs `pg_trgm`
  for the keyword case.
- **F4** — `nearby()` still materialises the whole latitude band into
  Python before paginating.
- **F5** — the admin overview is still 13 sequential full-table
  aggregates (five store `COUNT(*)`s that could be one `GROUP BY`).
- The vendor dashboard's biggest-store case on SQLite (see F1/F6 above) —
  a `PRAGMA optimize` / better-stats / forced-plan question, or Postgres.

---

## Consequences

- `tests/integration/test_scale_concurrency.py` — 7 tests, part of the
  suite, ~27 s. They assert the invariants, not timings, so they are not
  flaky.
- `scripts/measure_scale.py`, `scripts/loadtest.py` (now with `--wal`)
  and `scripts/measure_denylist.py` — re-runnable, write their `_*.md`
  companions next to this file.
- **First pass:** no production code changed. **Follow-up pass:** migration
  `bac2fb1331ba` (indexes), `get_products` eager loading,
  `_recalculate_rating` atomic, `with_write_retry` on checkout. F3, F4, F5
  remain the scale backlog.
