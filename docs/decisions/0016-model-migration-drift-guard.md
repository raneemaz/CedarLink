# 0016 — Model / migration drift, and a CI guard against it

**Date:** 2026-09-02
**Status:** accepted
**Queue item:** between 7 and 8 — cleanup, no feature work

## The two occurrences

By item 7, two places had the SQLAlchemy models and the Alembic migration
chain disagreeing. Neither was caught for weeks because nothing checks.

### 1. `notifications` indexes — the database was right

Commit `b2bdd09a` (2026-08-28) added the `Notification` model *and* its
migration in one go, and they disagreed from that first commit:

| | Model declared | Migration `c4a9e7f2105d` created |
|---|---|---|
| `user_id` | `ix_notifications_user_id` | `ix_notifications_user_id` |
| composite | — | `ix_notifications_user_is_read` `(user_id, is_read)` |
| composite | — | `ix_notifications_user_created_at` `(user_id, created_at)` |
| `created_at` | `ix_notifications_created_at` `(created_at)` | — |

Every notification query filters by `user_id` first: the list is
`WHERE user_id = X ORDER BY created_at DESC`, the unread count is
`WHERE user_id = X AND is_read = false`. A standalone `(created_at)` index
serves neither — it cannot seek by `user_id`. The `user_id`-leading
composites the migration hand-wrote are the correct design; the model's
`index=True` on `created_at` was a mistake.

**Resolved by amending the model** (`fix(notifications):` commit): the two
composites are now declared in `__table_args__` under their existing names,
and `index=True` is off `created_at`. No schema change — the database
already had the right indexes.

`ix_notifications_user_id` is kept. It is now a redundant leading-column
prefix of both composites and SQLite could answer every `user_id` lookup
from them. Dropping it is a real index change, which would turn this
model-only fix into a database migration for no measurable gain on a table
this size. The redundancy is deliberate and documented rather than an
oversight.

### 2. `payments.provider` nullability — the model was right

`c2d457aee7f3` created `payments` without `provider`. `62182cd5264a`
(hand-edited: *"Only add the missing payment columns"*) added it as
`nullable=True`. The model (`b75f92bc`) has always said `nullable=False`.

The only code that constructs a `Payment` — `payment_routes.create_payment`
— always sets `provider` to `PAYMENT_PROVIDERS[method]` (`"cedarlink"`),
a non-null constant. The seed command builds no payments; `tests/conftest.py`
has no payment factory. `NOT NULL` is the real invariant.

**Resolved with a migration** (`fix(payments):` commit), `0d106f16652f`.
SQLite cannot `ALTER COLUMN`, so it runs through `op.batch_alter_table`
(table rebuild), preceded by `UPDATE payments SET provider = 'cedarlink'
WHERE provider IS NULL` so the rebuild cannot fail on a legacy row even
though a from-empty database has none. `downgrade` reverses to
`nullable=True`; verified with a row present that upgrade → downgrade →
upgrade preserves the data and toggles the constraint both ways.

## The guard — `flask db check` in CI

A new CI step, **"Models and migrations agree"**, runs immediately after
"Migrations apply to an empty database":

```yaml
- name: Models and migrations agree
  run: flask db check
  env:
    DATABASE_URL: sqlite:////tmp/ci_migrations.db   # the DB the previous step built
```

`flask db check` (Flask-Migrate 4.1.0 / Alembic 1.18.4 — the version was
checked, not assumed; older Alembic lacks `command.check` and would need a
`flask db migrate` + grep-for-operations fallback) autogenerates a model↔DB
diff **in memory** and exits non-zero if it is not empty. It writes no
revision file, so there is nothing to keep out of the repo, and it reuses
the previous step's `/tmp/ci_migrations.db`, which is already outside the
working tree.

**What it actually proves — and what it does not.** `flask db check`
compares the models against *the database it is pointed at*. It does **not**
inspect the migration chain directly. It only tells us what we want —
"the migrations, applied from scratch, produce a schema the models agree
with" — *because the preceding CI step points it at a database built by
`flask db upgrade` from an empty file*. Run against any other database the
result would mean something else. This is written down here so the
guarantee is not later misremembered as stronger than it is: the guard is
"upgrade-from-empty then check", not "check the migrations".

It was seen to fail: adding an undeclared column to a model makes the step
exit 1 with `New upgrade operations detected: [('add_column', ...)]`;
reverting the column makes it pass again.

## Why CI and not a developer habit

The drift above is exactly what a habit misses. Both cases were introduced
by someone hand-editing a migration (reasonably — Alembic autogenerate
*does* get composite indexes and "column already exists" wrong) and not
re-running autogenerate afterward to confirm the model still matched. A
checklist item "remember to run `flask db check`" has the same failure mode
as the thing it guards. The machine runs it every push, on the same
from-empty database every time, and blocks the merge. Nobody has to
remember.

## What it costs

- **CI time:** one `flask db upgrade` already runs; `flask db check` adds a
  second in-memory autogenerate pass against that DB — a few seconds.
- **Friction:** a legitimate model change now *requires* its migration in
  the same PR or CI is red. That is the intended cost — it is the exact
  gap that produced both drifts.
- **False positives:** possible if Alembic's autogenerate cannot represent
  something the model expresses (it has known blind spots — CHECK
  constraints on existing tables, some server defaults). If one appears,
  the fix is an explicit `compare_*` exclusion in `migrations/env.py` with
  a comment, not disabling the step. None are needed today.
