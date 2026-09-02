# 0014 — Store announcements

**Date:** 2026-09-02
**Status:** accepted
**Queue item:** 6 (C.1 — store operations, third slice)

A vendor can post short notices to their store page — "Closed for Eid",
"New stock just in", "Delivery delayed today". `StoreAnnouncement(id,
store_id, title, body, starts_at, ends_at, is_active, created_at)`, with
`GET` public and `POST` / `PUT` / `DELETE` owner-only. Three decisions were
non-obvious.

## 1. Two independent gates: `is_active` **and** a time window

An announcement shows on the storefront only when `is_active` is true *and*
`starts_at <= now < ends_at` (`ends_at` NULL = open-ended). Either gate alone
was tempting and both are wrong on their own:

- **Window only.** A vendor who wants to pull a notice early has to edit the
  `ends_at` to a past time — fiddly, and it loses the original intent. A
  boolean off-switch is what they reach for.
- **`is_active` only.** "Closed next Friday for a wedding" has to be
  remembered and toggled twice, on the day and off again. A window lets the
  vendor schedule it once and forget it.

Real use needs both: schedule with the window, override with the switch. The
combined rule lives in exactly one place — `announcement_service.is_live()` —
and the model stays data-only (no logic on it), the same split the
store-hours code uses.

`starts_at` defaults to now, so the common case ("post this now, no end
date") needs neither field. Times are **naive UTC**, consistent with
`override_until` and every other timestamp in this schema (ADR 0013).

## 2. One `GET`, two audiences

`GET /api/stores/{id}/announcements` is `@jwt_required(optional=True)`. A
public caller gets only the live rows. The **owner** gets every row —
active, inactive, expired, not-yet-started — each with an `is_live` flag, so
the vendor console can list and re-activate old notices. A separate
owner-only listing endpoint would have been more endpoints for no gain; the
spec's "Public / Owner" on one row is exactly this behaviour.

## 3. Cap of 5 active per store, enforced on write

A store may have at most 5 `is_active` announcements. The store page is not a
billboard, and an unbounded list is a griefing and clutter risk once the
marketplace is public. Inactive/expired rows do not count, so history is not
capped — only what is shown. The check runs in the service on create and on
any update that would switch a row on.

## Promotions notification

Creating an active announcement emits a **best-effort** `promotions`
in-app notification to every customer who has an order from that store. It
reuses the existing `notification_service` machinery, so the per-user
`promotions` preference gate (default **off**) already applies — a customer
is notified only if they opted in. The emit runs *after* the announcement is
committed and never raises: a failure is logged and rolled back without
touching the announcement, the same isolation `_emit` gives the order
notifications. Edits and deletes do not re-notify — only the initial post.

## Migration

`a1b2c3d4e5f6` — one revision. Creates `store_announcements` indexed on
`store_id` and `created_at`. Verified on the dev database: `upgrade`,
`downgrade`, `upgrade` again all run clean.
