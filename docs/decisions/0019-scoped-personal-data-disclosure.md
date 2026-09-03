# 0019 — Scoped personal-data disclosure in serializers

**Date:** 2026-09-03
**Status:** accepted
**Queue item:** 8 (C.2 follow-ups from the item-8b `to_dict()` sweep)

The item-8b review swept every `to_dict()` in `app/models/` and found two
fields that were leaving through a public/shared payload because the
serializer was a dump, not an allowlist (CLAUDE.md). This records the fix
for both.

## 1. `Review.to_dict()` drops `user_id`

A review requires a **delivered order** that belongs to the reviewer
(ADR 0015). So a public review carries an implicit fact: "this person
bought this product." Exposing `user_id` on the public review list
(`GET /api/products/{id}/reviews`, `/api/stores/{id}/reviews`) turns that
list into a **scrapeable per-person purchase history** — pick a `user_id`,
collect every product and store they have reviewed.

`author_name` (the reviewer's *first name* only) stays. That is the
deliberate disclosure: enough to make a review feel written by a real
person, not enough to identify or track one. The stable numeric id was
never needed by any client and is gone from the base payload.

`admin_list_reviews` still needs to know who wrote a flagged review, so it
re-adds the id under `author.id`, explicitly — the same pattern used for
`moderation_note`.

## 2. `DeliveryAssignment` — the driver's phone is a scoped release

`driver_phone` is a **third party's personal mobile number**. It was a
plain field in `to_dict()`, so it reached the customer via
`GET /api/delivery/assignments/{id}` and stayed readable forever, long
after the order arrived.

The number is genuinely useful — a customer coordinating a handoff needs
to reach the driver — but only during a narrow window. So:

- `to_dict()` **omits** `driver_phone` by default. Callers opt in with
  `include_driver_phone=True`.
- **The vendor always gets it.** They assigned the driver and manage the
  delivery; it is operational data for them.
- **The customer gets it only while `status != "delivered"`.** During
  `assigned` / `picked_up` the delivery is in progress and coordination
  may be needed. Once the driver marks it `delivered`, the number
  disappears from the customer's view — there is no longer a reason for
  them to hold a stranger's mobile number, and nothing stores it.

`driver_name` stays visible to the customer throughout: "your driver is
Karim" is reassurance, not a contact handle, and cannot be used to reach
anyone.

There is no persistence change — the release is decided per request from
`assignment.status`, so a redelivery or a status correction takes effect
immediately.

## The general rule

Both cases are the same mistake and the same fix, now written into
CLAUDE.md: **a model's `to_dict()` is the payload for its least-privileged
reader.** Anything narrower — admin-only, owner-only, or time-boxed — is
added back by the route that has the context to decide, never carried by
default and filtered later.
