# 0022 — Customer interests: stated, not inferred

**Date:** 2026-09-04
**Status:** accepted
**Queue item:** customer interests

A customer picks up to five categories and the home page leads with them.
That is the whole feature. This ADR records what was deliberately *not*
built, and why the boring version is the right one here.

## The decision

**Ranking comes from what a customer said, never from what they did.**

There is no search-history table, no view counter, no "customers who
bought this also bought", and no derived affinity score anywhere. The only
input to the home page order is a row the customer created by ticking a
box in Settings.

Three reasons, in order of weight:

1. **A learned recommender at this data volume returns noise.**
   Collaborative filtering needs overlapping purchase histories to find a
   signal. CedarLink launches with a handful of stores; the honest output
   of a model trained on that is close to random, dressed up as insight.
2. **An untrained model in a report invites questions with no good
   answers.** "Why did it recommend that?" has no defensible reply when
   the model is fitted to fifty orders. "Because you chose Electronics,
   and it is first in your list" is answerable by anyone reading the
   page.
3. **It works from the first customer.** Behavioural ranking has a cold
   start: it is worst exactly when the marketplace is smallest. Stated
   interests are useful the moment somebody ticks a box, and they do not
   degrade as the catalogue grows.

The privacy position falls out of the same choice rather than being
bolted on: there is nothing to leak or to explain in a policy, because
nothing is collected. The settings page says so in as many words —
"CedarLink does not track what you browse or buy" — which is a claim the
code can actually back.

## What ranking means

**Promotion, never filtering.** An interest moves a category up the page;
it never removes one. A customer who picks Books still sees Grocery below
it. This is deliberate: a marketplace that hides categories from people
who did not think to ask for them is a marketplace where vendors outside
a customer's five picks become invisible, and neither the customer nor
the vendor agreed to that.

The order is:

1. Stated interests, **in the order the customer put them in** — hence
   `ShoppingInterest.position` rather than a plain set. Selection order is
   the cheapest possible signal of relative strength and it costs one
   integer.
2. Everything else, in the default order below.

Empty categories are dropped *after* ordering, not before, so an interest
in a category with nothing in it does not silently promote something else
into its slot.

## The default for customers who chose nothing

**Categories with the most visible products first, then by name.**

This is also what a signed-out visitor sees, and what a signed-in
customer sees until they pick something — one code path, not three.

Busiest-first is the honest guess when nobody has said anything: it is
the order most likely to have something worth showing, and it needs no
history to compute. The name tiebreak is not decoration — without it,
categories with equal counts reorder between requests depending on how
the database returns rows, and a home page that reshuffles on refresh
looks broken.

## Five

`MAX_INTERESTS = 5` is a product ceiling, not a storage limit. A customer
who picks every category has expressed no preference, and a home page
whose first screen is "all of it" is the thing this feature exists to
replace. The server enforces it; the settings form disables the remaining
chips at five so it cannot offer a save that will be refused.

## Storage

A table (`shopping_interests`), not a JSON column on
`shopping_preferences`:

- A deleted category cannot leave a dangling id behind.
- "Which customers care about category X" stays an ordinary query, for
  whenever someone wants that number.
- `position` has somewhere to live.

**The cascade is in the ORM, not the foreign key.** The FK declares
`ON DELETE CASCADE`, but SQLite ignores foreign-key actions unless
`PRAGMA foreign_keys=ON`, and this app does not set it — no other model in
the codebase uses `ondelete`, so nothing had depended on it before. The
delete that actually runs is `Category.interests` with
`cascade="all, delete-orphan"`, which works regardless of the pragma. The
DDL keeps its `ondelete` for a database that enforces it. **A bare
`ondelete=` in this codebase does nothing today** — worth knowing before
someone adds one and assumes otherwise.

## What was already there

`ShoppingPreferences` and its service predate this work and were
untested. They cover checkout convenience — address autofill, preferred
payment method, default delivery city — plus `hide_out_of_stock`.

Two things worth recording:

- **`hide_out_of_stock` is stored, editable, and read by nothing.** The
  product listing does not consult it. It is a preference that does not
  work. Left alone here rather than fixed in an interests session, but it
  should either be wired up or removed.
- The service now has tests, covering the pre-existing validation as well
  as interests. A whitelist validator is only worth having if something
  proves it rejects what it claims to.

## One endpoint, not one per category

`GET /api/home/sections` returns the ordered sections with their products.
The alternative — the client fetching categories, then one product
request per category — makes the page's cost scale with the catalogue and
puts the ordering rule in the browser, where it cannot be tested or
explained.

The endpoint is open to signed-out visitors and **never creates a
preferences row as a side effect of reading**. Asking how to sort a page
is not a reason to write to the database.

Both the listing and these sections build their product payload with
`app/utils/product_payload.product_card`. A second hand-written copy of
the same dict is how two endpoints drift apart.

## Consequences

- `shopping_interests` is new (migration `4348b45cc8e6`, verified
  up-from-empty, down, up, `flask db check` clean).
- The home page's four hardcoded category tiles are gone; it now shows the
  real categories, in the order it renders them.
- Nothing about checkout, orders, or pricing changed.
- If behavioural recommendation is ever wanted, it arrives as a *second*
  signal alongside this one, not as a replacement — the stated list is
  what makes any result explainable.
