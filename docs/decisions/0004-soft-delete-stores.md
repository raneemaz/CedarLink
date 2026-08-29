# 0004 — Stores are soft-deleted by admins

**Date:** 2026-08-29
**Status:** accepted
**Finding:** CL-24
**Queue item:** 3 (admin console)

## Context

`Store.orders` and `Store.products` were declared with
`cascade="all, delete-orphan"`. `DELETE /api/admin/stores/<id>` therefore
did a hard `db.session.delete(store)`, which cascaded into every `Order`
ever placed with that store — and from there into the customers'
`OrderItem`s and `Payment`s.

An administrator removing a misbehaving store would silently erase parts of
strangers' purchase history and the financial records attached to it. Same
class of problem as CL-23 (see [0003](0003-soft-delete-products.md)),
one level up.

## Decision

Stores are **soft-deleted**, mirroring products:

- `Store.deleted_at` (nullable `DateTime`). `NULL` means live.
- The `delete-orphan` cascade is removed from `Store.orders` and
  `Store.products`. Store, order, order-item and payment rows are never
  destroyed by a store removal.
- `DELETE /api/admin/stores/<id>` sets `deleted_at` and returns 200 with
  "Existing orders are preserved." A second delete returns 400.
- A `Store.is_visible` property (`is_active and deleted_at is None`) is the
  single storefront gate. Every place that already checked `is_active` —
  product list, product detail, cart add, checkout preview/create, store
  list, store detail — now uses `is_visible`, so a removed store is absent
  from the storefront exactly like a deactivated one.
- **Removed vs deactivated for the owning vendor:** a *deactivated* store's
  vendor keeps a working console (they can reactivate it). A *removed*
  store's vendor gets a "this store was removed by an administrator" notice
  instead — `deleted_at` is exposed on `to_dict()` and the vendor console
  layout checks it.
- Customer order history is untouched: `get_orders` / `get_order` filter by
  `user_id` and never check store visibility, and the store row still
  exists, so orders from a removed store render exactly as before.

## Consequences / known gaps

- No "restore store" flow. If ever needed it is a one-field update, but the
  admin console does not offer it yet.
- A removed store's products are not individually soft-deleted; they are
  hidden transitively. If a store were restored, its products return too —
  acceptable.
- Hard deletion (GDPR erasure of a vendor's data) remains unbuilt and would
  have to decide what to do with the order lines. Out of scope.
