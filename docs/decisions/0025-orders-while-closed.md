# 0025 — Orders while the store is closed

**Date:** 2026-09-05
**Status:** accepted

## The problem

`assert_store_open` refused a cart-add and a checkout whenever the store
was shut, for every store. That is correct for a restaurant and wrong for
a clothes shop: a customer browsing at 11pm should be able to buy
something that ships tomorrow.

The cost of getting it wrong is asymmetric and invisible. A refused sale
does not appear anywhere — the vendor never learns the order existed, so
there is no signal that the rule is losing them money. A shop selling
perishables has the opposite problem, and would be harmed by the
permissive default.

Neither behaviour is right for every store, so the store decides.

## The decision

`Store.accepts_orders_when_closed`, Boolean, NOT NULL, **default False**.

The default preserves the existing behaviour exactly, so no vendor's
store changes what it does because this shipped. Turning it on is a
deliberate act by someone who knows their own trade.

Enforcement stays in the service layer. `store_service.is_open_now`
remains the only thing that decides open/closed; the renamed
`order_service.assert_store_accepts_orders` decides whether *closed*
means *refuse*. Routes call it and nothing else — a route must not be
able to reach a different answer than checkout does.

## Schedule versus override — the distinction the feature turns on

**A store closed by its schedule** takes orders when the flag is set.
Being outside opening hours is a routine, predictable state; the vendor
knew about it when they set the schedule.

**A store closed by an active manual override refuses regardless of the
flag.** An override is the vendor saying *something is wrong right now* —
the power is out, a pipe burst, they have shut early. Letting orders flow
through it would make setting one pointless: the vendor would reach for
the control that means "stop" and orders would keep arriving.

Concretely, `assert_store_accepts_orders` only forgives
`CLOSED_OUTSIDE_HOURS`. `CLOSED_OVERRIDE` and `CLOSED_NOT_VISIBLE` refuse
whatever the flag says.

### The alternative not taken: a per-override "still accept orders" choice

The obvious generalisation is to put the choice on each override — "I am
closing for two hours, and yes/no you may still order". It was rejected
for three reasons:

1. **It asks the wrong question at the wrong moment.** An override is set
   in a hurry, usually because something has gone wrong. Adding a second
   decision to that flow gets it answered badly or not at all, and the
   default would end up carrying all the weight anyway.
2. **It makes the control mean two things.** Today "override closed"
   means one thing: nothing is happening here right now. With a per-
   override flag it would mean either that *or* "shut but still selling",
   and a vendor scanning their own store page could no longer tell which
   without opening the override.
3. **The case it serves is already covered.** A vendor who wants to keep
   selling while shut for the afternoon does not need an override at all
   — that is what the schedule and this flag are for. The override exists
   for the situation where they specifically do *not* want orders.

If a real need appears — a vendor closing for a week's holiday who still
wants to take orders for their return — the right shape is probably a
separate "holiday mode" with an end date, not an extra checkbox on an
emergency control.

## `next_opening_time`

`store_service.next_opening_time(store)` returns the next instant the
store opens, as an aware `Asia/Beirut` datetime, or `None` when the store
has no hours at all. A store with an empty schedule is never open, so
there is no honest answer to give.

It shares every edge case with `is_open_now`, because it reuses
`_row_covers`:

- **Split days.** 09:00–14:00 and 16:00–20:00 are two rows on one day; at
  15:00 the answer is 16:00 today, not 09:00 tomorrow.
- **Intervals crossing midnight.** A 20:00–02:00 row covers the evening on
  its own day and the small hours of the next. At 01:00 the store is
  already open, so the answer is *now*; the morning half is a
  continuation, not a fresh opening, so it is never a candidate.
- **An override expiring inside a closed period.** The store opens at the
  **later** of the two constraints. An override ending at 14:00 on a day
  scheduled 09:00–18:00 means the store opens at 14:00. One ending at
  03:00 does not pull the 09:00 opening earlier.

It looks ahead seven days and gives up after that. A weekly schedule with
any row in it always opens within seven days, so the cap only bites on
data that could not open anyway — it is a guard against a runaway loop,
not a real limit.

DST is handled by `ZoneInfo`, not by arithmetic: the schedule is local
wall-clock, so 09:00 the morning after Lebanon springs forward is still
09:00 (ADR 0013). Both transitions have tests.

## What the customer sees

One component, `ClosedStoreNotice`, on the store page, the product page
and the cart — three surfaces that must not disagree about whether a
shop will take money.

- Takes orders → *"Closed right now — opens Saturday 09:00. You can still
  order; it will be delivered after that."*
- Does not → *"This store is closed and is not taking orders right now."*

The opening time is formatted in **Asia/Beirut**, not the viewer's zone.
A customer in Paris reading "opens Saturday 09:00" means the shop's nine;
shifting it to their own clock would be a lie about when the door opens.

**The cart's old warning is gone.** `cart.storeClosedWarning` implied a
block for every closed store, which is now wrong half the time, so the
key was deleted rather than reworded — a string that is right by accident
is worse than one that is absent.

## What the vendor sees

Its own labelled section on `/vendor/store`, placed between the weekly
schedule and the override panel, so it reads in the order a vendor thinks:
*these are my hours* → *this is what happens outside them* → *this is how I
shut right now*.

Not a bare checkbox. The toggle's description changes with its state and
says what each one costs — with it off, "the sale is refused and you will
not hear about it", which is the part a vendor cannot otherwise discover.
The override caveat sits on the control itself in an amber box, because
it is the one thing that would otherwise surprise someone who set both.

## Consequences

- `stores.accepts_orders_when_closed` is new (migration `38b3517994a9`,
  verified up-from-empty, down, up, `flask db check` clean). NOT NULL
  with a server default of false, so existing rows are unchanged.
- `assert_store_open` is renamed `assert_store_accepts_orders`. Both
  callers were updated; no alias was kept, because a name that says
  "open" for a function that answers "accepts orders" is how the two
  concepts got conflated in the first place.
- The store payload gains `accepts_orders_when_closed` always, and
  `next_opening_time` only when the store is shut and still selling —
  computing an opening time for every open store in a directory listing
  would be work nobody reads.
- 21 tests cover the rule and the clock, including both DST transitions.
