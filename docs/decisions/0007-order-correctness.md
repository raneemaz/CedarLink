# 0007 — Checkout correctness: atomic stock, Decimal money, no leaked errors

**Date:** 2026-08-30
**Status:** accepted
**Queue item:** 4, session 3 (correctness fixes — CL-06, CL-07, CL-20)

These three landed together in `order_service` now that it exists (0006).

## CL-06 — the oversell race

**Was:** checkout read `product.stock` into Python, checked it, and later
did `product.stock -= qty` against that now-stale value. Two checkouts for
the last unit both passed the check and both committed.

**Now:** `order_service._reserve_stock` decrements in one statement:

```sql
UPDATE products SET stock = stock - :qty WHERE id = :id AND stock >= :qty
```

`rowcount == 0` means the units went between pricing and here — it raises
the same `"Insufficient stock"` 400 the pre-check raises (now reporting the
live on-hand count). The Python pre-check in `price_cart` stays as the
fast, friendly path for the ordinary "you asked for 5, there are 3" case.

Migration `e5a6b7c8d9f0` adds `CHECK (stock >= 0)` on `products` — the last
line of defence, since the column allowed negatives.

### Test determinism

`test_concurrent_checkout.py` was `xfail(strict)` and XPASSed ~1 run in 30:
the old harness synced both threads on their first `Session.get`, then let
them race to commit, so sometimes one committed before the other read.

The new harness holds every checkout thread at a `threading.Barrier` the
instant it finishes pricing — every stock read done, nothing written, **no
lock held** (pysqlite doesn't start a transaction for SELECT, so the read
path holds nothing). All threads release together and race the write path;
SQLite serializes the writers and the conditional UPDATE picks the winners.
Outcome depends on nothing but the SQL. 20/20 consecutive green, plus a
second test (3 buyers, stock 2 → exactly 2 succeed).

## CL-07 — money was Float in one place

`Product.price` was `Float`; `Order.total_price`, `OrderItem.unit_price`,
`Payment.amount` and both store delivery fees are `Numeric(10, 2)`.
Checkout multiplied the float by a quantity and assigned into Numeric.

- Migration `f6b7c8d9e0a1`: `products.price` → `Numeric(10, 2)`.
- `order_service` prices entirely in `Decimal` — subtotal, fee, per-store
  total, cart total. `float()` happens only in `serialize_quote` and the
  checkout response: the JSON boundary, nowhere earlier.
- The product list/detail serializers wrap `price` in `float()` because
  `jsonify` cannot emit `Decimal`.
- Product **CRUD** still accepts a JSON number and lets SQLAlchemy store it
  into the Numeric column — on SQLite that round-trips back to a clean
  2-place `Decimal`, verified. Not worth touching input parsing.

`test_checkout_total_is_exact_not_float_drifted`: `0.10 × 3` comes back as
`0.30` (not `0.30000000000000004`) from `/orders/preview` and `/orders`,
and persists as `Decimal("0.30")`.

## CL-20 — internal exception text reached the client

`checkout` returned `{"error": "Checkout failed", "details": str(e)}` —
leaking table, column and constraint names.

`app/utils/errors.py` → `register_error_handlers(app)`:

- `HTTPException` (routing, method-not-allowed, `abort()`) → `{"error":
  <description>}` JSON instead of Werkzeug's HTML.
- Anything unhandled → a generic message plus a `correlation_id`; the id
  and the full stack trace go to the log, nothing else to the client.
- `internal_error(exc, context)` is the same 500 for a view that catches
  its own exception. The three `order_routes` 500 branches use it.

Explicit `return jsonify({...}), 4xx` responses in views are **not**
exceptions, so every error body the test suite asserts on is untouched —
this standardises the uncaught paths only.

Under `TESTING` Flask re-raises unhandled exceptions rather than running
the `Exception` handler, so the tested path is the view-level
`internal_error` in checkout (forced 500 → generic body + correlation id,
no leak). The global handler is verified to work in a real app context.

## Consequences

- `pytest` is fully green, **no xfail**: 55 passed.
- Two new migrations (`e5a6b7c8d9f0`, `f6b7c8d9e0a1`); both up/down tested
  on a fresh SQLite DB. `flask seed` still works against the new schema.
- Deferred to 4d: security hardening and CI.
