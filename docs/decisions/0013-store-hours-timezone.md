# 0013 — Store hours: timezone, storage, and midnight

**Date:** 2026-08-31
**Status:** accepted
**Queue item:** 6 (C.1 — store operations, first slice)

Stores now carry a weekly opening schedule (`StoreHours`) and a manual
open/closed override (`Store.override_*`). `app/services/store_service.py`
is the single place that answers "is this store open now"; the order service
turns a closed answer into the standard `OrderError` at cart-add and
checkout. This record covers the three decisions that could have gone
another way.

## 1. DST — resolve "now" through `ZoneInfo("Asia/Beirut")`, never an offset

Lebanon observes daylight saving: **EET (UTC+2)** in winter, **EEST
(UTC+3)** in summer. A vendor who sets "open until 21:00" means 21:00 on the
clock on their wall, in both seasons.

`store_service._now_local()` is `datetime.now(ZoneInfo("Asia/Beirut"))`.
`zoneinfo` applies the correct offset for the current date automatically, so
"21:00 local" is always the right instant with no seasonal code. A fixed
`timezone(timedelta(hours=2))` would be wrong for half the year;
`datetime.utcnow()` is banned by `CLAUDE.md` and would be wrong always.

`zoneinfo` needs the IANA database. It is present on Linux (CI, production)
but **not** on Windows, so `tzdata` is now a hard dependency in
`requirements.txt` — it is the portable fallback `zoneinfo` looks for.

**The transition-hour edge case is accepted, not handled.** Twice a year the
local clock skips or repeats an hour around 03:00. A schedule row that
brackets that hour is off by up to 60 minutes for that one night. Beirut
shops are closed at 3 a.m.; special-casing a fold/gap here would be more
code than the problem is worth. It is written down so it is a known gap, not
a bug.

## 2. Store the schedule as naive local wall-clock time

`StoreHours.opens_at` / `closes_at` are `Time` columns holding **naive local
Beirut time** — "09:00" is the literal string a vendor typed. `is_open_now`
takes today's Beirut date + time and checks membership directly.

The alternative — storing each interval as a pair of UTC instants — is worse
here:

- Opening hours are *recurring*, not tied to a date. A UTC instant needs a
  reference date to exist, and the right offset depends on which side of a
  DST boundary that date falls, so "09:00 every Monday" would need
  re-materializing twice a year.
- What the vendor sees in the editor and what the customer sees on the store
  page is wall-clock time. Storing it that way means no conversion on read
  and nothing to get wrong.

`Store.override_until` is different: it is a single moment, not a recurring
one. It is stored as **naive UTC**, consistent with every other timestamp in
this schema (`created_at`, `deleted_at`, …), serialized with an explicit
`+00:00`, and compared against `datetime.now(timezone.utc)`.

## 3. `closes_at <= opens_at` means the interval crosses midnight

A row `(Mon, 20:00, 02:00)` reads as "Monday 20:00 until Tuesday 02:00". The
morning portion belongs to the following day.

`is_open_now` at `(weekday W, local time T)` checks every row whose day is
`W` **or** `W-1`:

- `opens_at < closes_at` — a same-day interval. Open iff row day is `W` and
  `opens_at <= T < closes_at`. The close is exclusive: at exactly `17:00` a
  `09:00–17:00` store is closed.
- `closes_at <= opens_at` — crosses midnight. Open iff
  *(row day is `W` and `T >= opens_at`)* — the evening half — **or**
  *(row day is `W-1` and `T < closes_at`)* — the morning half spilling out
  of the previous day.

`PUT /hours` **rejects `opens_at == closes_at`** as almost certainly a
mistake rather than treating it as a 24-hour day. Genuine round-the-clock
opening is expressed as a normal interval (e.g. `00:00–23:59`, or a
midnight-crossing pair). `is_open_now` still tolerates an equal-times row if
one is constructed directly (tests, fixtures) — it falls into the
midnight-crossing branch — but the API will not create one.

**Overlap validation is per weekday.** Two intervals on the same
`day_of_week` may not overlap; touching endpoints (one closes at `12:00`,
the next opens at `12:00`) are fine. A midnight-crossing interval is
projected onto its own day as `[opens_at, 24:00)` for this check — its spill
into the next day's early hours is a different weekday and is not
cross-checked against that day's rows. That corner (a late-night interval on
Monday overlapping an early interval on Tuesday) is left unvalidated;
`is_open_now` still resolves it correctly, a customer would just see "open"
from either row.

## Enforcement

`order_service.assert_store_open(store)` raises
`OrderError(code="store_closed", …)` — a distinct code alongside the
existing `error` message shape. It is called from `cart_routes` when an item
is added and again inside `price_cart`, so cart-add and checkout apply the
same single rule, the way `price_cart` is the single source of pricing
truth (CL-15). A soft-deleted or deactivated store is `not is_visible` and
therefore never open, regardless of its schedule.

## Override lifecycle

An override wins while `override_until` is in the future. Once it passes it
is **ignored on read and never written** — `is_open_now` just falls through
to the schedule. A background sweep to null out stale overrides can come
later; it is not needed for correctness. `PATCH /override` rejects a missing
or past `until` and an `until` more than 7 days out, so an override cannot
silently strand a store closed for a month.

## Migration

`d6f1a2b3c4e8` — one revision. Creates `store_hours` (indexed on
`store_id`) and adds the three `override_*` columns to `stores` via batch
mode. Verified on an empty database: `flask db upgrade` builds it,
`flask db downgrade` drops it cleanly, `upgrade` again rebuilds it.
