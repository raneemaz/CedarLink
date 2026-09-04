# 0023 — Foreign key enforcement

**Date:** 2026-09-04
**Status:** accepted (test only; production deferred)

## The problem

**Every foreign key in this schema was declared and none was enforced.**

SQLite parses `FOREIGN KEY` clauses and stores them in the schema, but it
does not act on them unless `PRAGMA foreign_keys=ON` is issued — and the
pragma is **per connection**, not per database. This project never issued
it, from any code path. At the time of writing that is 36 foreign keys
across 26 tables, all inert.

This is wider than the `ondelete` finding recorded in ADR 0022. That noted
that a declared `ON DELETE CASCADE` did nothing. The real situation is
that the *constraints themselves* did nothing: nothing stopped an order
row pointing at a store id that had never existed, or a review pointing at
a deleted user. The database was accepting whatever the application handed
it.

Nothing had gone wrong because the application layer had been careful.
That is not the same as the database being correct, and it is not a
property anyone can check by reading code.

## The decision

**Enable it in the test configuration, and only there, for now.**

`tests/conftest.py` registers a SQLAlchemy `connect` listener on `Engine`
that issues the pragma for every SQLite connection the suite opens. On
`Engine` rather than one engine, because the pragma is connection-scoped
and a pool opening a second connection would otherwise silently fall back
to unenforced. Guarded on the dialect, so a non-SQLite backend is left
alone.

### The result

**All 294 tests pass with foreign keys enforced.**

That is the finding this session was looking for, and it is a good one:
the schema is consistent under real enforcement. No test inserts an
orphan, no teardown deletes a parent out from under a child, and no
fixture depends on a dangling reference. The suite deletes tables in
reverse dependency order, which is why teardown survives too.

The pass was checked to be meaningful before it was believed. A probe
confirmed `PRAGMA foreign_keys` reads back as `1` inside the app context,
and that inserting a product with a non-existent `store_id` now raises
`IntegrityError` where it previously succeeded. A green suite against an
inactive pragma would have proved nothing.

## Why production is deferred

Turning this on in development and production is a **behaviour change**,
not a configuration tidy-up, and the code freeze is on 28 September.

What changes on the day it is enabled:

- Writes that currently succeed start raising `IntegrityError`. Every one
  of those is a latent bug, but it surfaces as a 500 to a user rather than
  as a test failure.
- Deletes that currently orphan children start failing, or start
  cascading, depending on the `ondelete` clause each constraint carries —
  and most carry none, which means `NO ACTION`, which means the delete is
  refused.
- **The existing production database may already contain rows the
  constraints would reject.** Enabling the pragma does not retroactively
  validate existing data — `PRAGMA foreign_key_check` does. If that
  returns rows, they have to be cleaned before enforcement can be turned
  on, or the first delete that touches them fails.

None of that is hard. It is simply not something to discover in the week
before a freeze, on a change whose upside is "a class of bug we have no
evidence of having" — the test suite now demonstrates the schema is
consistent, which is most of the value at a fraction of the risk.

## What enabling it would involve

For whoever picks this up after the freeze:

1. Move the listener out of `tests/conftest.py` into the application
   factory, registered against `db.engine` (or `Engine`, same reasoning as
   above), so every connection gets it.
2. Run `PRAGMA foreign_key_check` against a copy of the production
   database. It returns one row per violating row: table, rowid, parent
   table, and which constraint. An empty result means the data is already
   clean.
3. Clean anything it reports, or decide per case that the row should be
   deleted.
4. Audit the `ondelete` clauses. Almost none are set today, so the default
   is `NO ACTION` — a parent delete is refused rather than cascading.
   Anywhere the application currently relies on an ORM-level
   `cascade="all, delete-orphan"` (`Cart.items`, `Order.items`,
   `Category.interests`, `ShoppingPreferences.interests`) that keeps
   working, because SQLAlchemy issues the child deletes itself. The risk
   is the places that do a bulk `Model.query.filter_by(...).delete()`,
   which bypasses the ORM cascade.
5. Enable it in `DevConfig` first and run the app for a while before
   `ProdConfig`.

## Consequences

- The test suite is now evidence about the schema, not just about the
  code. A future migration that introduces an inconsistent relationship
  fails the suite instead of being accepted silently.
- ADR 0022's note that "a bare `ondelete=` does nothing in this codebase"
  remains true in development and production, and is now false in test.
  The ORM-level cascade on `Category.interests` is still the one that runs
  everywhere, so nothing depends on which environment it is.
- Production behaviour is unchanged by this session.
