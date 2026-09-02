# 0017 — Review moderation: report, flag, remove, restore

**Date:** 2026-09-02
**Status:** accepted
**Queue item:** 7 (C.3 — reviews & ratings, item 7c)

Reviews are user-generated content on a public marketplace, so they need a
moderation path. This record covers the three decisions in it that could
have gone another way.

## 1. A report flags; only removal hides and de-counts

`POST /api/reviews/{id}/report` lets **any authenticated user** report a
review once, with a reason (`ReviewReport`, unique on `(review_id,
user_id)`). The first report on a `published` review moves it to
`flagged`.

A **flagged** review is unchanged for the public: it still appears in the
listing and still counts toward `rating_avg` / `rating_count`. `flagged`
means only "an admin should look at this". The admin's **remove** is the
single action that both hides the review (gone from public listings) and
drops it from the average.

The alternative — hiding a review the moment it is reported — was
rejected. One motivated user (or a vendor with a second account) could
report every negative review and make them all vanish until an admin
worked through the queue, with the store's rating inflated in the
meantime. Tying *both* effects to a human decision (removal) closes that.
It also keeps the rating honest: a card that says "3.2 (10)" always has 10
visible reviews behind it.

`published → flagged → removed`, and `flagged`/`removed → published`
(restore). An admin may also flag directly, or remove a still-`published`
review without the flag step. `removed → removed` and the like are
rejected as no-ops.

## 2. Every status change goes through one function

`review_service._transition(review, new_status, note)` is the only place a
review's `status` is written. It sets the status, records the admin's
reason on `moderation_note`, bumps `updated_at`, and **recomputes the
target's rating in the same transaction**. `report_review` and
`moderate_review` both call it; there is no path that changes status
without the recompute, the same way `_recalculate_rating` already can't be
skipped on create/edit/delete (ADR 0015).

This **refines ADR 0015**: the counting set is now *every status except
`removed`* (`COUNTING_STATUSES = published, flagged`), not `published`
alone. `_recalculate_rating`'s `WHERE` changed from `status = 'published'`
to `status IN (...)` accordingly.

## 3. Removed reviews are kept, not deleted

A `removed` review's row stays in the table — invisible to everyone except
an admin, restorable in one click. Same reasoning as soft-deleted products
(ADR 0003) and stores (ADR 0004): a moderation call can be wrong, a false
report happens, and an audit trail is worth more than the row. The
`ReviewReport` rows are kept too — they are the evidence the admin acted
on. (An author deleting *their own* review still hard-deletes it, taking
its reports with it via `delete-orphan`; there is nothing left to
moderate.)

The admin queue (`GET /api/admin/reviews`, default filter = the `flagged`
set, which is exactly "needs a decision" — a report always flags, and
remove/restore both clear the flag) shows the review, its target, the
author, and each report's reason and reporter. It `selectinload`s reports,
author, product and store so the page is a fixed number of queries
regardless of size.

## Deferred — vendor reply

A vendor reply (one per review, shown beneath it, editable by the store
owner) is **not** in this slice. Done properly it needs a vendor-facing
reviews surface to edit replies from, which is its own piece of work;
half-wiring it (storage + display, no real editing surface) would be worse
than leaving it for later. It is listed in the roadmap (Part C.3) and
stays there.

## Migration

`3a61552ad9fa` — `review_reports` table (unique `(review_id, user_id)`,
indexed on `review_id`) and `reviews.moderation_note`. `flask db migrate`,
reviewed, verified `upgrade` from empty / `downgrade` to base / `upgrade`
again, and `flask db check` clean.
