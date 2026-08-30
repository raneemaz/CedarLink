# 0006 — Extract order_service; make Store.is_visible a hybrid

**Date:** 2026-08-30
**Status:** accepted
**Queue item:** 4, session 2 of 3 (pure refactor — no behaviour change)

## Context

Two duplications had been flagged in the code review:

- **CL-15** — `checkout_preview()` and `checkout()` in `order_routes.py`
  shared ~80 lines: cart grouping, stock validation, store lookup,
  delivery-availability check, inside/outside fee selection, subtotal
  arithmetic. The quote endpoint and the charge endpoint each carried
  their own copy. If one changed and the other didn't, a customer would be
  quoted one total and charged another — silently.
- **Store.is_visible** — the storefront visibility rule (approved AND
  active AND not removed) existed as a Python `@property` plus three
  hand-written SQL filters (product list, product detail, store list),
  noted as drift-prone in 0005. It is security-relevant: a drifted copy
  leaks a pending or removed store onto the storefront.

`order_routes.py` had also grown route handlers of 100–180 lines, against
the project rule of ~40, and still used the legacy `Model.query.get()`
(CL-22).

## Decision

### Pricing lives in one function

`app/services/order_service.py` — `price_cart(user_id, delivery_city)` is
the single implementation. It groups the cart by store, validates each
product and its stock, resolves each store, picks the inside- or
outside-city fee, and returns per-store subtotals/fees/totals plus the
resolved ORM objects.

- `POST /api/orders/preview` calls `price_cart` and serializes the quote.
- `POST /api/orders` calls `price_cart`, then persists one order per store
  from the same result.

The fee calculation now appears in exactly one place. (The seed script,
`app/cli.py`, computes historical demo-order totals with its own copy —
that is fixture generation, not the checkout path, and is left alone.)

### The rest of the order logic moved too

`checkout`, order listing, order detail, vendor orders, status transitions
and cancellation are all service functions. Route handlers parse the
request, call one function, and serialize — the largest is now 32 lines.

Business-rule failures raise `OrderError(message, status_code, **extra)`,
which carries the exact JSON body the route returns, so the one error
shape is unchanged. The generic `500` fallbacks (`"Checkout failed"`,
`"Failed to update order status"`, `"Failed to cancel order"`) stay in the
route, byte-for-byte, including the pre-existing `str(exception)` leak in
the checkout 500 — fixing that is CL-20, not this session.

### Store.is_visible is a hybrid_property

`@hybrid_property` + `@is_visible.expression` (`and_(...)`). The same
definition now works as `store.is_visible` in Python **and**
`Store.is_visible` inside `filter()`. The three SQL filters were replaced
with `filter(Store.is_visible)`; the two Python checks already used the
property. One definition, four call sites.

The always-on `Store.deleted_at.is_(None)` join filter in the product list
stays explicit: the vendor-owned branch there needs "not removed" *without*
the active/approved clauses, so it is a genuinely different predicate.

### CL-22 in the touched files

`Model.query.get()` / `.get_or_404()` → `db.session.get()` in
`order_routes.py`, `product_routes.py` and `category_routes.py`. The
`get_or_404` sites now return the same JSON `404` shape the rest of those
files use (`{"message": "... not found"}`) instead of Werkzeug's HTML
page. All 10 `LegacyAPIWarning`s in the test run are gone.

## Consequences

- The test suite is unchanged and still reports **46 passed, 1 xfailed**.
  The suite is the contract for this refactor.
- `order_routes.py` dropped from ~650 to ~170 lines.
- New surface to keep thin: `order_service.py`. Route handlers must not
  regrow — they call one function and serialize.
- Not addressed here (session 4c): CL-06 the oversell race, CL-07, CL-20.
  The `test_concurrent_checkout` xfail still documents CL-06.
