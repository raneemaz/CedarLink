# 0003 — Products are soft-deleted

**Date:** 2026-08-29
**Status:** accepted
**Finding:** CL-23
**Queue item:** 2 (vendor console — product management)

## Context

`Product.order_items` was declared with `cascade="all, delete-orphan"`.
Deleting a product therefore deleted every `OrderItem` that had ever
referenced it. Those `OrderItem` rows are the only record of what was in a
past order and at what price — removing them silently rewrites order
history and breaks the stored totals of orders that are already delivered
and paid.

A marketplace cannot let a vendor's "delete this product" action mutate a
customer's completed order.

## Decision

Products are **soft-deleted**:

- `Product.deleted_at` (nullable `DateTime`). `NULL` means live.
- The `delete-orphan` cascade is removed from `Product.order_items`. The
  product row and its `OrderItem` rows are never destroyed.
- `DELETE /api/products/<id>` sets `deleted_at` and still returns `200`.
  A second delete returns `404`.
- Soft-deleted products are excluded from `GET /api/products`, return
  `404` from `GET /api/products/<id>`, are rejected by cart-add, and stop
  checkout (preview and create) with a `400` naming the product —
  never a `500`.
- Cart items pointing at a deleted product are left in place; the customer
  gets a clear "remove it from your cart" message at checkout.
- Order history is unaffected: `OrderItem` already stores `unit_price`,
  and the `Product` row still exists, so `item.product.name` and the line
  total keep rendering exactly as before.

## Consequences

- Every product query that feeds the storefront must filter
  `deleted_at IS NULL`. New list endpoints must remember this.
- A soft-deleted product's name can still be read through order history —
  acceptable, and necessary.
- Hard deletion, if ever needed (GDPR erasure, spam cleanup), becomes an
  admin-only operation that must also decide what to do with the order
  lines. Out of scope here.
- No unique constraint on product name, so "deleting" then re-adding a
  product with the same name just creates a new row — fine.
