# 0009 — Auth throttling, registration privacy, and CI

**Date:** 2026-08-30
**Status:** accepted
**Queue item:** 4, session 4 — closes item 4 (CL-10 + CI)

## CL-10a — auth endpoints were unthrottled

`Flask-Limiter` on the endpoints an attacker probes:

| Endpoint | Per IP | Per account |
|---|---|---|
| `/auth/login` | 10 / min | 5 / min |
| `/auth/register` | 5 / min | 5 / hour |
| `/auth/login/resend`, `/register/resend`, `/2fa/resend` | 5 / min | — |
| `/auth/password-reset/request` | 5 / min | 5 / hour |

Per-IP stops one host hammering. Per-account (key = the `email` in the
request body) stops a botnet spreading a credential-stuffing run for one
victim across many IPs — the per-IP limit alone misses that entirely.

Storage is in-memory: correct for a single gunicorn worker, per-process
only with several. Production with multiple workers sets
`RATELIMIT_STORAGE_URI` to a shared Redis. Recorded, not built — there is
no Redis in the stack yet.

Under tests the limiter stays installed (so its behaviour is exercised) and
conftest resets its storage after every test, so counts never leak between
tests. Two tests deliberately blow past the limits and assert `429`.

## CL-10b — registration enumerated accounts

`/register` answered `400 "Email already exists"` for a taken address — a
free oracle: an attacker learns which emails have accounts without any
authentication.

Now a taken email gets the **same** `201` and the same challenge payload a
free email gets (`decoy_registration_challenge`): a random challenge token
that verifies to nothing, no user row, no code sent. The password is still
hashed on the decoy path so response time matches the real one. `user_id`
was dropped from the success response too — it is unused by the client, and
a sequential id is itself an oracle.

Residual: timing is *approximately* equalised, not constant-time. Closing
that fully (e.g. always enqueue a send) is a later refinement.

## CI

`.github/workflows/ci.yml`, on every push and PR:

**Backend** — `flake8 app tests run.py`; `flask db upgrade` against an
empty SQLite database (the check that would have caught the broken
migration chain fixed in item 1); `pytest`.

**Frontend** — `npm ci`, `npm run lint`, `npm run build` on
**ubuntu-latest**. Linux is case-sensitive, so the build step is what
catches an import that only resolves on Windows/macOS
(`pages/settings` vs `pages/Settings`).

`.flake8` pins `max-line-length = 100` and ignores `E203`/`W503`. It lints
application code only — `files related/` holds one-off doc-render scripts,
and the space in that path defeats flake8's exclude matching, so CI names
`app tests run.py` explicitly.

CI surfaced a latent bug from item 4a: the suite only ran under
`python -m pytest` (which puts the CWD on `sys.path`), not the bare
`pytest` console script CI uses — `import app` in `conftest.py` failed with
`ModuleNotFoundError`. Fixed with `pythonpath = .` in `pytest.ini`, which
works for both invocations. This is exactly the class of problem CI exists
to catch.

The README carries the build-status badge.

## Consequences

- New dependencies: `Flask-Limiter` (+ `limits`, `Deprecated`,
  `ordered-set`, `wrapt`) and `flake8`, all pinned.
- `main` now has a gate: a red build blocks merge.
- Tests: `tests/regression/test_auth_hardening.py`.
