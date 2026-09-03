# 0021 — Coupons and discounts

**Date:** 2026-09-03
**Status:** accepted
**Queue item:** coupons (backend)

Two models (`Coupon`, `CouponRedemption`), validation in
`coupon_service`, application inside `order_service.price_cart`. This
records the four decisions that were not obvious.

## 1. A platform-wide *fixed* coupon is refused on a multi-store cart

A CedarLink cart becomes **one order per store**. Each order has its own
vendor, its own delivery fee, its own lifecycle, and can be cancelled on
its own. So a discount has to land on a specific order — there is no
"basket" object to attach it to.

A **percentage** distributes with no ambiguity. 10% off a cart holding
100 from store A and 60 from store B is 10 off A and 6 off B, and those
parts sum to 16, which is exactly 10% of 160. Applying it per store and
applying it to the whole basket give the same answer, so per store it is.

A **fixed amount** has no such answer. "$20 off" a cart of A=100 and B=60
could be:

| split | A | B | objection |
|---|---|---|---|
| proportional | 12.50 | 7.50 | see below |
| first store | 20.00 | 0 | arbitrary; depends on dict order |
| evenly | 10.00 | 10.00 | ignores basket sizes |
| in full to each | 20.00 | 20.00 | gives away 40 for a 20 coupon |

**Proportional distribution is the alternative design, and it was not
taken.** It is defensible arithmetic and it is what most large
marketplaces do. It was rejected here for three reasons:

1. **It does not survive cancellation.** Cancel order B and the customer
   keeps only the 12.50 that landed on A — they were promised 20 off and
   got 12.50, for a reason no interface can explain in one line. To fix
   that you have to re-spread the remaining 7.50 onto A after the fact,
   which means editing the price of an order that already exists. That is
   precisely the thing ADR 0007 exists to prevent.
2. **It does not round cleanly.** 20 across three stores is 6.67 + 6.67 +
   6.66, and someone has to own the stray cent. Every scheme for
   allocating it is arbitrary and every one of them is a place for the
   quoted total and the charged total to drift apart (CL-15).
3. **The vendor accounting becomes fiction.** Store B's order says it
   discounted 7.50 of a coupon it never issued and cannot see.

Refusing the combination costs the customer one clear message —
`coupon_fixed_multi_store`, its own error code — instead of a silent
mis-split. Store-scoped fixed coupons are unaffected: they name exactly
one order by construction. If proportional distribution is ever wanted,
it needs a basket-level discount record that survives a partial
cancellation, which is a bigger change than a coupon column.

## 2. The discount comes off goods, never delivery

`coupon_service.discount_for` is handed a **goods subtotal** and nothing
else. The delivery fee is added afterwards and is never in scope.

A delivery fee is a real cost the store incurs to move the box. It does
not get smaller because the goods sold for less, and a coupon that ate it
would be the platform quietly billing the vendor for its own promotion. A
test puts a 100%-off coupon against a store with a fee and asserts the
total is exactly the fee.

`min_order_total` is measured against the same goods subtotal, **before**
the discount. Checking it after would let a coupon pull a basket under
its own minimum and still apply — a rule that stops being a rule the
moment it binds.

## 3. The clamp

The discount is clamped to the goods it is discounting:

```python
return min(_money(raw), _money(goods_subtotal))
```

So a store's goods portion can fall to zero but never below it, and a
store total lands at its delivery fee. No total is ever negative, and the
platform never owes a customer money for shopping. This is a clamp on the
*discount*, not a subtraction that is later floored — the recorded
`amount_applied` is what was actually taken off, not what the coupon
nominally offered, so the audit trail stays honest about a $500 coupon
spent on $10 of goods.

## 4. Redemption is a conditional UPDATE — the fourth appearance

**ADR 0007** established the pattern for stock: never read-then-write a
counter that concurrent requests share. The claim is one statement and
the database decides the winner.

```sql
UPDATE coupons SET used_count = used_count + 1
 WHERE id = :id AND (usage_limit IS NULL OR used_count < usage_limit)
```

A rowcount of 0 means somebody took the last use between pricing and
here, and raises the same `coupon_usage_limit` error the pre-check would
have. This is now the fourth place the shape appears:

1. stock decrement at checkout (ADR 0007, CL-06)
2. store-hours override claim
3. the TOTP counter high-water mark (ADR 0020, fixed this session — it
   had been written read-compare-write and was losing updates)
4. coupon `used_count`

The pattern is cheap to write and the failure it prevents is invisible in
testing unless you go looking, which is why #3 shipped broken. Both #3
and #4 have a `threading.Barrier` test held at the read/write seam, and
both were checked against the naive implementation first: each one fails
there and passes here. **A concurrency test that has never been seen to
fail is not evidence of anything.**

`per_user_limit` has no counter column — it is a count of redemption rows
— so it is re-checked inside the transaction after the row is inserted
rather than trusted from validation time.

## 5. A use is consumed per order, and cancellation gives it back

`used_count` counts **orders**, not checkouts, and there is exactly one
`CouponRedemption` row per discounted order. This falls out of the
per-order structure above: each order independently records what it took,
so each order can independently give it back.

`cancel_order` releases the redemption in the same block that restores
the stock, for the same reason and with the same shape:

```python
for item in order.items:
    product.stock += item.quantity     # give back the goods
...
coupon_service.release(redemption.coupon_id, order.id)   # give back the use
```

The redemption row is deleted and `used_count` decremented, so a cancelled
order leaves the coupon exactly as it found it and the code works again. A
test cancels a `usage_limit=1` order and re-uses the code.

**Consequence worth stating:** a platform-wide percentage coupon on a
two-store cart consumes **two** uses, because it discounts two orders.
`validate_for_cart` therefore checks the limits against the number of
orders the cart will produce, not against 1 — otherwise a preview would
succeed where the checkout then fails, which is exactly the quote/charge
divergence CL-15 exists to prevent.

## 6. Smaller decisions

- **Codes are stored normalised** (trimmed, uppercased) so the unique
  index *is* the case-insensitive lookup — no `LOWER()` on the column, no
  collation dependency, and no way to create two coupons differing only
  in case.
- **A vendor cannot create a platform-wide coupon** because the vendor
  routes never read `store_id` from the body; it comes from the URL. There
  is no payload that widens a vendor's scope. Asserted by test, including
  a `"store_id": null` in the body being ignored on both create and edit.
- **The client's discount is never read.** `price_cart` computes it from
  the coupon record; the checkout handler takes only `coupon_code` off the
  body. A test posts `discount: 99999` alongside a real code and asserts
  the charged total is unchanged.
- **A redeemed coupon deactivates instead of deleting.** A redemption row
  is order history and points at the coupon; destroying it would break
  both the audit trail and the FK. An unredeemed coupon has no history to
  protect and is deleted outright.
- **The applied code lives on the cart**, not in the client, so it
  survives a reload and `DELETE /api/cart/coupon` has something to clear.
  It is stored as the code rather than an FK: the coupon is re-validated
  on every pricing run anyway, and a code that has since been deleted must
  fail validation, not break the cart.
- **`amount_applied` is recorded, not recomputed.** A coupon's value can
  be edited afterwards, so the only trustworthy answer to "what discount
  did this order get?" is the number written when it was placed.

## Consequences

- `coupons` and `coupon_redemptions` are new; `carts` gains a nullable
  `coupon_code` (migration `5b79a62a0984`, verified up-from-empty, down,
  up, `flask db check` clean, CHECK constraints confirmed live).
- Every existing pricing test passes unchanged — `price_cart` gained an
  optional third argument and the quote gained two keys, so no caller and
  no assertion had to move.
- Nothing is stored on `Order`. The discount is recoverable from the
  redemption row, and `total_price` is already the charged figure.
