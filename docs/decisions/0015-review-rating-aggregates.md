# 0015 — Reviews: recompute rating aggregates, never increment

**Date:** 2026-09-02
**Status:** accepted
**Queue item:** 7 (C.3 — reviews & ratings, backend)

`Product` and `Store` each carry `rating_avg` (`Numeric(3,2)`, nullable) and
`rating_count` (`Integer`, default 0). These are denormalized so a product
or store card can show "4.6 (23)" without a join and an aggregate on every
list render — the two most expensive queries in the discovery roadmap.

The question this record answers: when a review is written, edited, deleted
or moderated, **how** do those two numbers get updated.

## Decision — one aggregate query, in the same transaction

`review_service._recalculate_rating(kind, entity)` runs exactly:

```sql
SELECT AVG(rating), COUNT(*)
FROM reviews
WHERE <product_id = :id | store_id = :id> AND status = 'published'
```

and writes the result onto `entity.rating_avg` / `entity.rating_count`. It
is called inside the caller's transaction on **create, update, delete, and
status change** — the four events that can change the published set for a
target. `rating_avg` is `NULL` when there are no published reviews.

## Why not increment the counters

The obvious cheap version is `rating_count += 1` and a running-sum update of
the average. It is wrong here for the **same reason** the checkout stock
decrement is a single conditional `UPDATE` and not a read-then-write —
**CL-06, ADR 0007**:

> checkout read `product.stock` into Python, checked it, and later did
> `product.stock -= qty` against that now-stale value. Two checkouts for the
> last unit both passed and both committed.

Two reviews landing on the same product in overlapping transactions would
each read `rating_count = 5`, each write `6`, and one increment is lost. The
average drifts further every time it happens and there is no way to notice
or repair it without … recomputing from the rows. Edits and moderation make
it worse: "this review went from 2★ to 5★" or "this review was removed" is
not expressible as an increment at all without also storing the old value
and trusting it.

Recomputing sidesteps all of it. `AVG`/`COUNT` over an indexed
`(product_id, status)` / `(store_id, status)` filter is a cheap query on the
tens-to-hundreds of reviews a single product or store accumulates, it is
**self-healing** (any drift is erased on the next write), and it is the same
code path for create, edit, delete and moderation. The write already holds
a transaction; the recompute joins it and commits atomically with the
review change, so a reader never sees a review without its effect on the
average or vice versa.

If a product ever accumulates enough reviews that the recompute is
measurably slow, the fix is a trigger or a materialized rollup — still a
recompute, just moved. It is not an increment.

## Related constraints (not aggregate-related, recorded here for one place)

- **Verified purchase.** A review requires a `delivered` order owned by the
  reviewer that actually contains the target (product by order item, store
  by `order.store_id`). Enforced in `review_service`, rejected with a
  distinct `code`.
- **Exactly one target.** A `CHECK` — `(product_id IS NOT NULL AND store_id
  IS NULL) OR (product_id IS NULL AND store_id IS NOT NULL)` — defined in
  the initial `create_table` because SQLite cannot `ALTER … ADD
  CONSTRAINT`.
- **One review per (user, order, target), and it takes two unique
  constraints.** `(user_id, order_id, product_id)` and `(user_id, order_id,
  store_id)`. A single index on the first cannot see two store reviews of
  the same order as a collision: both have `product_id` NULL and `NULL !=
  NULL` in SQL, so the uniqueness check passes. The second index catches
  those; the first catches duplicate product reviews. Both are needed.
- **No cascade from Order, Product or Store.** A review is verified-purchase
  evidence and outlives a soft-deleted product exactly like an order item
  does.

## Migration

`a128e4a1eead` — `flask db migrate`, then trimmed. Autogenerate rendered
the `reviews` table (with both CHECKs and both unique constraints inline in
`create_table`, as required) and the four `rating_*` columns correctly; it
also surfaced **pre-existing drift** unrelated to this change — the
`notifications` composite indexes were replaced by single-column ones in the
model without a migration, and `payments.provider` is `NOT NULL` in the
model but nullable in the DB. Those were removed from this revision and left
for their own fix. Verified: `upgrade` from empty, `downgrade` to base,
`upgrade` again — all clean.
