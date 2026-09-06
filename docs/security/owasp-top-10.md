# CedarLink against OWASP Top 10:2025

One row per category. "What CedarLink does" is the current behaviour;
"Proof" is a named test or ADR that demonstrates it; "Not addressed" is
where the honest answer is *nothing*, or *not enough*.

This is not a claim that CedarLink is secure. It is a map of where the
work is and where the gaps are. The gaps are collected in
[ADR 0033](../decisions/0033-security-pass.md). There has been **no
penetration test** and no external review.

Generated / verified: 2026-09-07. Tooling wired into CI: `bandit -r app/
-ll`, `pip-audit -r requirements.txt`, `npm audit --audit-level=high`.

---

## A01 — Broken Access Control

**What CedarLink does.** Every mutating route is behind `@jwt_required()`
plus either `@role_required(...)` or an ownership check in the service
layer. Roles are `customer` / `vendor` / `admin`; public registration can
only mint the first two (`PUBLIC_REGISTRATION_ROLES`), admin is CLI-only.
Cross-tenant reads are keyed to the caller's id (`filter_by(user_id=...)`,
`_load_owned_store`, `product.store.owner_id`), returning 403/404 rather
than another tenant's data. Public visibility of a store is one hybrid
property, `Store.is_visible` (ADR 0006).

**Proof.**
- `tests/security/test_access_control_customer_isolation.py` — customer A
  cannot read B's orders, addresses, notifications or saved cards by id;
  the id-bearing route list is enumerated from `url_map`, so a new
  unclassified `/api/.../<int:id>` route fails the suite.
- `tests/security/test_access_control_vendor_isolation.py` — vendor B is
  refused on A's store, products, coupons, announcements, hours, override,
  status and social links; `/api/vendor/*` is checked for data isolation.
- `tests/security/test_access_control_admin_routes.py` — every
  `/api/admin/...` route (and the admin-only category writes) refuses a
  customer and a vendor; a completeness assertion fails if a new
  admin-prefixed route is added without a test.
- `tests/integration/test_two_factor.py::test_a_challenge_issued_for_one_user_cannot_be_used_by_another`
- ADR 0019 (scoped personal-data disclosure), ADR 0005 (store approval
  gate).

**Fixed in this pass.** `GET /api/vendor/orders` had `@jwt_required()`
only, not `@role_required("vendor")` — inconsistent with its two siblings.
A customer reached it (and got a 404, not a leak, because they own no
store). Now guarded; covered by the vendor-isolation suite.

**Not addressed.** No field-level authorisation framework — each route
carries its own check, so coverage is only as good as the test
enumeration above. No object-level rate limiting (an authorised user can
enumerate their own resources as fast as they like).

---

## A02 — Security Misconfiguration

**What CedarLink does.** `ProdConfig.validate()` refuses to start if
`SECRET_KEY`, `JWT_SECRET_KEY` or `TWO_FACTOR_ENCRYPTION_KEY` are unset —
no silent fallback to the committed dev placeholders (ADR 0001). `DEBUG`
is `False` in production. `flask seed` refuses to run when
`FLASK_CONFIG=production`. Error responses are one shape and never carry
exception text (A10). CORS is an origin allowlist (`CORS_ORIGINS`), not
`*`. A dead debug route (`GET /api/auth/test-admin`, returning "Welcome
Admin!") was removed in this pass.

**Proof.** ADR 0001 (config split), `tests/regression/test_error_handling.py`,
ADR 0007 §CL-20.

**Not addressed — this is a real gap.**
- **No security headers.** The app sends no `Strict-Transport-Security`,
  `X-Content-Type-Options: nosniff`, `X-Frame-Options`,
  `Referrer-Policy` or `Content-Security-Policy`. TLS is assumed to be
  terminated by a proxy that is not part of this repo, and nothing
  enforces HTTPS or HSTS from the app.
- **CORS default is developer-local.** With `CORS_ORIGINS` unset the
  allowlist is `localhost:5173-5175`. In production it must be set
  explicitly; nothing warns if it is not.
- **`PRAGMA foreign_keys` is OFF in dev and prod.** SQLite ignores every
  `FOREIGN KEY` clause unless the pragma is issued per connection.
  CedarLink issues it only in the test suite (ADR 0023), so foreign-key
  enforcement is *tested* but not *deployed*. The ORM-level cascades run;
  the database-level ones do not.
- No hardened container / deployment manifest in the repo; runtime
  posture (worker count, reverse proxy, TLS, log shipping) is out of
  scope of the codebase and undocumented.

---

## A03 — Software Supply Chain Failures

**What CedarLink does.** `requirements.txt` is fully pinned;
`frontend/package-lock.json` is committed and CI installs with `npm ci`.
As of this pass, three scanners run on every push and fail the build:
`pip-audit -r requirements.txt`, `npm audit --audit-level=high`,
`bandit -r app/ -ll`.

**Proof.** `.github/workflows/ci.yml` (the three new steps), ADR 0033 §1.

**Findings from this pass.**
- `nanoid < 3.3.18` (GHSA-2v37-7h3g-55p8, high) — transitive via
  `postcss`, build-time only. **Fixed** by `npm audit fix`.
- `pytest 8.3.4` → CVE-2025-71176 (predictable `/tmp/pytest-of-*` on
  multi-user hosts). **Fixed** by pinning `pytest==9.0.3`; full suite
  still green.
- Environment-only (not in `requirements.txt`, so not gated): `pip`,
  `setuptools` in the venv carry install-time path-traversal advisories.
  These are build-toolchain hygiene, recorded in ADR 0033, resolved by
  keeping the toolchain current in CI images.

**Not addressed.** No SBOM, no dependency provenance / signature
verification, no pinning by hash. Transitive dependencies are trusted.

---

## A04 — Cryptographic Failures

**What CedarLink does.** Passwords are stored as `scrypt` hashes
(Werkzeug default, n=32768) — never reversible, never logged. TOTP secrets
are Fernet-encrypted at rest (`encrypt_totp_secret`); recovery codes and
challenge tokens are stored only as hashes. JWTs are HS256 signed with an
env secret. **No card number, PAN hash, or CVV is ever accepted or
stored** — the endpoint rejects PAN-shaped fields outright (ADR 0024).

**Proof.**
- `tests/integration/test_two_factor.py::test_the_totp_secret_is_encrypted_at_rest`,
  `::test_recovery_codes_are_stored_hashed`,
  `::test_the_challenge_token_is_stored_hashed_not_in_plaintext`
- `tests/integration/test_password_reset.py::test_the_new_password_hash_is_stored_not_the_password`
- `tests/integration/test_no_card_data.py` (29 tests), ADR 0024.

**Not addressed.** No transport-layer guarantee from the app (see A02 —
no HSTS). JWT signing strength depends entirely on the deployed
`JWT_SECRET_KEY`. The Fernet key `_PLACEHOLDER_FERNET_KEY` is committed —
used only under `TestConfig`, and `ProdConfig` requires a real key, but a
committed key material string is a smell. No key rotation story for the
TOTP-encryption key.

---

## A05 — Injection

**What CedarLink does.** All database access is through SQLAlchemy 2.0 —
parameterised queries, ORM expressions, `text()` with bound parameters.
The API speaks JSON; React escapes interpolated values by default. The one
place a vendor string reaches an HTML attribute — social-link `href`s — is
normalised server-side to an allowlist of `http`/`https`/`mailto`/`tel`,
so a `javascript:` URL cannot be stored (ADR 0026).

**Proof.**
- `bandit -r app/ -ll` — clean. The only raw SQL string
  (`f"DELETE FROM {table}"` in the dev-only reset helper) interpolates a
  name from a fixed module constant, is guarded by `_refuse_in_production`,
  and carries an inline `# nosec B608` with the reason.
- `tests/integration/test_store_social_links.py` — `javascript:`,
  `data:`, `file:` schemes rejected with 400; ADR 0026.

**Not addressed.** Keyword product search is `ILIKE '%term%'` across six
columns with no sanitisation of `%` / `_` wildcards — not an injection
(still parameterised) but a minor query-shaping quirk, noted in ADR 0032.
No output-encoding audit of every React render path.

---

## A06 — Insecure Design

**What CedarLink does.** Several design decisions are recorded precisely
because the secure option was the non-obvious one:
- Lost-update races are prevented by conditional `UPDATE ... WHERE
  <condition>` with rowcount-0 as the refusal — stock, coupon limits, the
  TOTP replay counter (ADR 0007). Verified at 50 concurrent threads
  (ADR 0032, `tests/integration/test_scale_concurrency.py`).
- A public serializer is an allowlist, not a dump; scoped fields
  (moderation notes, the driver's phone number) are added back by the
  route with the context to decide (ADR 0019).
- Reviews require a delivered order; the public review hides the author's
  account id so the list is not a scrapeable purchase history (ADR 0019).
- CedarLink keeps **no behavioural profile** — interests are stated, never
  inferred (ADR 0022).
- Card selection at checkout moves no money; cash on delivery is the only
  settlement (ADR 0024).

**Proof.** ADRs 0007, 0015, 0017, 0019, 0021, 0022, 0024, 0032.

**Not addressed.** No formal threat model document (STRIDE / attack
trees). This OWASP map and ADR 0033 are the closest thing. No abuse-case
tests for business logic beyond the ones listed (e.g. coupon-stacking
across sessions, review-bombing rate).

---

## A07 — Authentication Failures

**What CedarLink does.** Two-factor is real: TOTP (RFC 6238, one-time-use
enforced by a high-water-mark counter claimed with a conditional UPDATE),
email, and SMS/WhatsApp via Twilio. Recovery codes are single-use and
hashed. Login and password-reset are rate-limited **per IP and per
account** (ADR 0009). Registration and password-reset are written to be
account-enumeration resistant — a taken email gets the same 201 and a
decoy challenge as a free one; every password-reset refusal (unknown,
deleted, deactivated, suspended, unverified) is byte-for-byte identical to
success. Tokens are revoked on logout, password reset, and admin
suspension (bulk, via `tokens_revoked_at`; ADR 0008).

**Proof.**
- `tests/integration/test_two_factor.py` (~25 tests): replay, challenge
  binding, exhaustion, encryption at rest.
- `tests/integration/test_password_reset.py`: `test_every_refusal_reason_looks_identical_to_success`,
  `test_the_reset_code_is_single_use`, `test_resetting_the_password_kills_tokens_issued_before_it`.
- `tests/regression/test_auth_hardening.py`: enumeration + throttling.
- `tests/integration/test_token_revocation.py`: `test_suspended_users_live_token_is_rejected_on_the_next_request`.

**Fixed in this pass.** `POST /api/auth/register` enforced **no** password
length — a one-character password was accepted, while the reset flow and
the admin CLI both required 8. Now `MIN_PASSWORD_LENGTH = 8` at
registration too (`tests/regression/test_auth_hardening.py::test_registration_rejects_a_short_password`).

**Not addressed.** Length floor only — no complexity rule, no
breached-password (HIBP) check. Access tokens live 15 minutes, refresh
tokens 30 days with **no rotation** on use. No device/session list, no
"log out everywhere" beyond the events that already bump
`tokens_revoked_at`. No CAPTCHA or progressive delay beyond the fixed
rate-limit buckets.

---

## A08 — Software or Data Integrity Failures

**What CedarLink does.** Migrations are reviewed by hand and CI runs
`flask db upgrade` from empty plus `flask db check` — a model changed
without a matching migration fails the build (ADR 0016). Denormalised
aggregates (`rating_avg`, `used_count`, stock) are **recomputed or
conditionally updated, never blindly incremented** (ADRs 0007, 0015). The
frontend design-token layer has its own guard so colour cannot drift back
into an undocumented second palette (ADR 0028). Lockfiles are committed.

**Proof.** ADR 0016 + the CI "Models and migrations agree" step;
`tests/integration/test_scale_concurrency.py::test_50_reviews_on_one_product_leave_a_consistent_aggregate`.

**Not addressed.** No CI artifact signing or provenance (SLSA). No
integrity check on uploaded product images beyond extension and size.
**The review-aggregate recompute is race-safe on SQLite only** — it does
an unlocked `SELECT` then a separate `UPDATE`, which SQLite serialises but
an MVCC database would not; a concurrent overwrite could store a stale
`rating_count` on Postgres (ADR 0032 §4). No `SELECT ... FOR UPDATE` and
no trigger.

---

## A09 — Security Logging and Alerting Failures

**Largely unaddressed. This is the weakest category and the honest answer
is "almost nothing".**

**What CedarLink does.** 500s are logged with a correlation id that is
also returned to the client (ADR 0007 §CL-20). Account lifecycle events
(deactivate / delete / reactivate) and a few 2FA send failures write an
`INFO`/`WARNING` line. Some security-relevant state changes leave a column
behind — `suspension_reason`, `moderation_note`, `approval_note`.

**Not addressed.**
- **No security audit log.** Failed logins, lockouts (429s), password
  resets, 2FA disable, recovery-code use, admin actions (suspend, approve,
  reject, remove store, moderate review) produce **no dedicated,
  structured, tamper-evident log entry.** There are 13 `logger.*` calls in
  the entire `app/` tree.
- **No alerting of any kind.** Nothing pages, emails, or posts on a burst
  of failed logins, a spike of 500s, a `database is locked` storm
  (ADR 0032), or an admin action.
- Logs go to Flask's default handler (stderr) with no structured format,
  no request id on non-error lines, no retention policy, and no shipping
  to anywhere durable.
- No log of *who* an admin action was taken by beyond the mutation itself.

Closing this is a project of its own: a structured audit-event sink, an
append-only store, and at minimum threshold alerts on auth failure rate
and 5xx rate.

---

## A10 — Mishandling of Exceptional Conditions

**What CedarLink does.** One error shape for the whole API,
`{"error": <message>}`, plus a `correlation_id` on unexpected failures.
**Exception text, table names and constraint names never reach the
client** — they are logged against the correlation id (ADR 0007 §CL-20).
Unknown routes and method-not-allowed return JSON, not Werkzeug's HTML.
Every route that catches its own exception calls `db.session.rollback()`
first. Concurrency edge cases (two buyers, the last unit) resolve
deterministically to one winner and one clean refusal, not a 500
(ADR 0007, verified at 50 threads in ADR 0032).

**Proof.**
- `tests/regression/test_error_handling.py`:
  `test_checkout_500_hides_exception_text_and_returns_a_correlation_id`,
  `test_unknown_api_route_returns_json_not_html`,
  `test_put_missing_product_returns_json_404`.
- `tests/integration/test_concurrent_checkout.py`,
  `tests/integration/test_scale_concurrency.py`.

**Not addressed.** Under heavy concurrent write load SQLite raises
`sqlite3.OperationalError: database is locked`, which surfaces as a
generic 500 with a correlation id — correct *containment*, but there is
**no retry, no backoff, and no circuit breaker**, so a fraction of
checkouts fail outright at ~100 concurrent writers (ADR 0032 §3). The
external HTTP calls (exchange rate, Twilio) have timeouts but no retry
policy. `get_rates()` degrades gracefully; a Twilio failure raises to the
caller.
