# 0027 — Vendor dashboard analytics

**Date:** 2026-09-05
**Status:** accepted

## The problem

A vendor could see their orders one at a time and nothing about the shape
of them. No sense of what sells, what earns, whether last week was better
than the one before, or how much money is actually in hand.

The hard part is not the arithmetic. It is deciding what each number
means, because several of the obvious ones are wrong in ways that look
right.

## What revenue is — and is not

**Revenue is goods sold minus discounts given.**

The delivery fee is not the store's money. It is collected from the
customer at the door on the driver's behalf and settled with the driver
afterwards. Putting it in a figure labelled "revenue" tells a vendor they
earned money they are about to hand over — so `delivery` is reported as
its own clearly labelled pass-through card, styled apart from the money
cards, with the words "Owed to the driver. Not part of your revenue."
Nothing in the payload or the interface ever adds it into a revenue
total.

Discounts are reported too, not just netted off silently. A vendor who
gave away $200 in coupons this month should be able to see that number
next to what it bought them.

## Collected is not the same as expected

CedarLink is cash on delivery. The money arrives when the order does, so
"an order exists" and "the money is in the till" are different facts and
the dashboard reports them as two blocks:

| | Statuses | Meaning |
|---|---|---|
| **Collected** | `delivered` | Money in hand. |
| **In progress** | `pending`, `processing` | Money owed, not yet received. |
| *(neither)* | `canceled` | Money that will never arrive. |

A cancelled order appears in the status breakdown and in the total order
count, and in no money figure and no unit count — those goods went back
on the shelf. The test
`test_an_order_cancelled_after_being_processed_leaves_in_progress` pins
the case that breaks a naive "everything not delivered is coming": an
order that was in progress and is now nothing.

`average_order_value` is on the same basis as the headline: collected
revenue over delivered orders. Zero delivered orders gives zero, never a
division by nothing.

## One aggregate query per figure

Seven queries, and the same seven whether the store has three orders or
thirty thousand. `test_the_query_count_does_not_grow_with_the_number_of_orders`
counts statements with one order and again with twenty-five, and asserts
the two are equal — which is what stops a loop over orders being added
later without anyone noticing.

Money is read, never recomputed. `order_items.unit_price` is the price at
the time of sale, `coupon_redemptions.amount_applied` is what the coupon
actually took off, `orders.delivery_fee` is what was charged. No pricing
rule runs again here; a dashboard that re-derives a price is a second
place for the price to be wrong (CL-15). As a cross-check,
`test_revenue_is_goods_minus_discount_and_matches_the_stored_totals`
asserts the computed revenue equals `total_price - delivery_fee` summed
over the same orders — the schema's other representation of the same
money.

Two queries for the top-product tables rather than one sorted twice.
"Most units" and "most revenue" are different questions, and each is an
`ORDER BY … LIMIT 5` the database can answer without shipping every
product to Python. The busiest day is the one exception: it is taken from
the per-day series already in hand, because a second query for the
maximum of a list we are holding is a query for nothing.

## Scope is not a parameter

Every query filters on `Order.store_id`. `store_dashboard` takes a
resolved `Store`, never an id, and the route looks that store up by
`owner_id` from the token. There is no request a vendor can make that
reaches another store's rows — including
`?store_id=<someone else's>`, which is tested and ignored.

This is a security test, not a feature test. An analytics endpoint that
forgets whose store it is answering about discloses a competitor's
takings, their best sellers and their customers' behaviour. The test
signs in as a second vendor, asserts the figures differ, and asserts no
product id from either store appears in the other's payload.

## Days are Beirut days

`created_at` is naive UTC (ADR 0013) and a vendor thinks in local days,
so the range is resolved as Beirut dates and converted to UTC instants
for the `WHERE` clause — `ZoneInfo` resolves the offset at each specific
instant, so a range straddling a DST change gets the right boundary on
both sides.

The per-day buckets use a single offset read from `ZoneInfo` at the end
of the range (so +2 in winter, +3 in summer — never hardcoded). A range
that spans a DST transition therefore misfiles orders placed in the one
changed hour on the far side of it. That is a bounded, documented
inaccuracy, and it is the price of keeping the bucketing to one aggregate
query; the fix, if it ever matters, is a stored local-date column rather
than a per-row timezone conversion in SQL.

## Best rated needs two reviews

A single five-star review is one customer's opinion, not a rating, and it
would otherwise sit above a product with forty reviews at 4.8. The
minimum is two.

The list reads the stored `rating_avg` / `rating_count` maintained by
`review_service` (ADR 0015) rather than recomputing an average, and it is
deliberately *not* filtered by the period: a rating is a standing fact
about a product, and a store with a quiet month has not stopped being
well rated.

## The chart is CSS

A flex row of divs, no charting library. The smallest of them costs more
transferred bytes than the entire vendor console, for one bar chart.

RTL comes out of the layout rather than out of a mirrored copy of it. A
flex row lays its children along the inline axis, so under `dir="rtl"`
the series reads right-to-left on its own; the axis follows with
`border-s` / `border-b` and `ps-`, which put it on the right in Arabic
and the left in English without either being named. Verified in the
browser: in English the axis border is on the left and day one sits at
x=54 with day thirty at x=228; in Arabic the border is on the right and
the same two are at x=219 and x=45.

## Empty and thin are different screens

- **No orders at all** — an explanation, and no cards. A grid of zeros
  and an axis with no bars reads as broken software rather than as a new
  store.
- **Orders, none delivered** — the cards are shown, because they are
  true, with a banner saying nothing has been collected yet and pointing
  at the in-progress figure. Checked against the seeded pending-approval
  store, which has exactly one pending order.

## Deliberately not built

Both were ruled out before any code, and both were checked rather than
assumed:

- **A cash/card split.** Checkout writes no `Payment` row and calls no
  provider; the table has zero rows in a fully seeded database. Every
  order is cash on delivery, so a split would chart a distinction the
  system does not record. (See also ADR 0024.)
- **Store and product view counts.** There is no view or visit column
  anywhere in the schema. Adding one means a write on every page load,
  which is a performance decision and a visitor-privacy decision, and
  neither has been made.
