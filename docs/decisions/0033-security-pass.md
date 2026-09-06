# 0033 — Security pass

**Date:** 2026-09-07
**Status:** accepted

A real security pass: automated scanning wired into CI, an OWASP Top
10:2025 map, three authorisation invariants verified by test, and the
residual risks written down. **CedarLink is not claimed to be secure.**
There has been no penetration test and no external review. This ADR is the
list of what was checked, what was fixed, and what is still open.

The category-by-category map is [`docs/security/owasp-top-10.md`](../security/owasp-top-10.md).

---

## 1. Automated scanning (CI, three new gates)

Same pattern as the schema-drift, token and contrast guards: the check
runs on every push and fails the build, so a regression cannot land
quietly.

| Gate | Command | Where |
|---|---|---|
| Python SAST | `bandit -r app/ -ll` | backend job, after lint |
| Dependency CVEs (Python) | `pip-audit -r requirements.txt` | backend job |
| Dependency CVEs (JS) | `npm audit --audit-level=high` | frontend job, after `npm ci` |

`bandit` and `pip-audit` are pinned in `requirements.txt`.

### bandit — 0 high, 3 medium (all resolved), 6 low (all false positives)

| Severity | Location | Test | Verdict |
|---|---|---|---|
| MEDIUM | `exchange_rate_service.py` `urlopen` | B310 | **Fixed** — see below |
| MEDIUM | `two_factor_service.py` Twilio `urlopen` | B310 | **Fixed** — see below |
| MEDIUM | `cli.py` `f"DELETE FROM {table}"` | B608 | False positive, `# nosec B608` + reason |
| LOW | `cli.py` `DEMO_PASSWORD = "Cedar!2026"` | B105 | FP — demo seed only, `_refuse_in_production`; `# nosec` |
| LOW | `config.py` `_PLACEHOLDER_SECRET` | B105 | FP — `ProdConfig` refuses to boot with it; `# nosec` |
| LOW | `two_factor_service.py` `PASSWORD_RESET_PURPOSE = "password_reset"` | B105 | FP — a purpose enum value, not a secret; `# nosec` |
| LOW ×2 | `auth_routes.py` `"5 per minute"` / `"5 per hour"` | B105 | FP — Flask-Limiter rate strings; below the `-ll` gate, listed here |
| LOW | `auth_routes.py` `PASSWORD_RESET_REQUEST_MESSAGE` | B105 | FP — a deliberately vague user-facing message (anti-enumeration); below the `-ll` gate |

**The CI gate is medium-and-above (`-ll`).** The six LOW findings are all
B105 string-pattern matches with no security content; three carry an
inline `# nosec B105` where the pattern is understandable (a name
containing "password"/"secret"), and the other three (rate-limit
literals, the anti-enumeration message) are documented here rather than
annotated, because a `# nosec` on `"5 per minute"` would be noise. A new
MEDIUM or HIGH finding fails the build.

**B310 fix.** `urllib.request.urlopen` follows `file://` and other schemes
if handed one. CedarLink's two outbound calls (exchange rate, Twilio) use
config- or literal-derived URLs, never request input, so this was a
false positive — but the cheap correct hardening is a scheme allowlist.
New `app/utils/safe_http.py::safe_urlopen` refuses anything that is not
`http`/`https` before the call; both call sites now use it, and the one
`# nosec B310` sits on a line whose scheme was validated immediately
above.

### pip-audit — 1 finding in the declared surface, fixed

- `pytest 8.3.4` → **CVE-2025-71176** (GHSA-6w46-j5rx-g56g): predictable
  `/tmp/pytest-of-{user}` directory allows a local user on a shared host
  to cause a DoS or possibly escalate. Fixed in 9.0.3. **Pinned
  `pytest==9.0.3`**; the full suite (500 tests) still passes.

**Environment-only, not gated** (not in `requirements.txt`, so
`pip-audit -r requirements.txt` does not see them — deliberately, because
the build toolchain is not a CedarLink dependency): `pip 25.3` (6
install-time path-traversal / archive-confusion advisories, fixed 26.1+)
and `setuptools 65.5.0` (6 advisories incl. `package_index` RCE via
download, fixed progressively through 78.1.1 / 83.0.0). These are CI-image
hygiene — keep the base image's `pip`/`setuptools` current. Recorded here
rather than pretended away.

### npm audit — 1 high, fixed

- `nanoid < 3.3.18` (**GHSA-2v37-7h3g-55p8**, high): a custom generator
  with `size = 0` loops forever. Transitive via `postcss` (build-time
  only; not shipped to the browser). Fixed by `npm audit fix` →
  `nanoid 3.3.18`; `package-lock.json` diff is that one line, build and
  lint still pass.

---

## 2. OWASP Top 10:2025 map

Full table in `docs/security/owasp-top-10.md`. Summary of where the
honest answer is "not addressed":

| Category | State |
|---|---|
| A01 Broken Access Control | Strong; enumerated tests. One missing guard **fixed** this pass. |
| A02 Security Misconfiguration | **Partial.** No security headers; CORS default is dev-local; **`PRAGMA foreign_keys` OFF in prod**. |
| A03 Software Supply Chain | Now gated (this pass). No SBOM / provenance / hash-pinning. |
| A04 Cryptographic Failures | Strong (scrypt, Fernet, no card data). No app-level TLS/HSTS. Committed Fernet placeholder. |
| A05 Injection | Strong. ORM throughout; one guarded raw-SQL constant. |
| A06 Insecure Design | Strong on the recorded decisions. **No formal threat model doc.** |
| A07 Authentication Failures | Strong (2FA, throttling, enumeration resistance). Password floor **fixed** this pass; still no complexity / breach check; no refresh rotation. |
| A08 Software/Data Integrity | Migration-drift gate; recompute-not-increment. Review aggregate is race-safe **on SQLite only** (ADR 0032). |
| A09 Security Logging & Alerting | **Largely unaddressed.** 13 log calls in `app/`; no audit log; no alerting. |
| A10 Mishandling Exceptional Conditions | Strong containment (one error shape, correlation id, no leak). No retry/backoff on `database is locked` (ADR 0032). |

A table of ten green ticks would not be credible. A09 is close to empty
and A02 has real holes.

---

## 3. Three authorisation claims, verified by test

Routes are enumerated from `app.url_map`, not hand-listed, and each suite
carries a completeness assertion so a route added later without the right
guard fails the build.

### `tests/security/test_access_control_customer_isolation.py`
Customer A cannot read or write customer B's orders, addresses,
notifications or saved cards by id — every probe returns 403/404, never
200-with-B's-data and never a 500. `test_no_unclassified_customer_id_route`
fails if a new `/api/.../<int:id>` route is neither classified as a
per-customer resource nor explicitly excluded.

### `tests/security/test_access_control_vendor_isolation.py`
Vendor B is refused (403/404) on vendor A's store update, hours, location,
override, status, announcements, social links and coupons, and on A's
products and product images. `/api/vendor/store` and `/api/vendor/dashboard`
are checked for *data* isolation (no id to tamper with).
`test_every_store_and_vendor_route_is_classified` is the rot guard.

### `tests/security/test_access_control_admin_routes.py`
Every `/api/admin/...` route, plus the admin-only category writes, refuses
a customer (403) and a vendor (403) and an anonymous caller (401/422); an
admin is allowed through (control). `test_every_admin_prefixed_route_is_covered`
fails if a new admin-prefixed route is not in the tested set.

**13 new tests, all green. 500 backend tests total** (was 487).

---

## 4. Fixes shipped in this pass

| # | Finding | Category | Fix |
|---|---|---|---|
| 1 | `GET /api/vendor/orders` had `@jwt_required()` only, not `@role_required("vendor")` — a customer reached it (404, no leak, but inconsistent with its two siblings) | A01 | Added `@role_required("vendor")`; covered by the vendor-isolation suite |
| 2 | `POST /api/auth/register` enforced **no** password length — a 1-char password was accepted, while reset and the admin CLI required 8 | A07 | `MIN_PASSWORD_LENGTH = 8` at registration; two new tests |
| 3 | Dead debug route `GET /api/auth/test-admin` returning `{"message": "Welcome Admin!"}` in the production url_map | A02 | Route and view deleted; unused `role_required` import removed |
| 4 | `bandit` B310 — `urlopen` with no scheme restriction (×2) | A05 / SSRF hardening | `app/utils/safe_http.py::safe_urlopen` — http/https only |
| 5 | `pytest` CVE-2025-71176 | A03 | Pinned `pytest==9.0.3` |
| 6 | `nanoid` GHSA-2v37-7h3g-55p8 (high) | A03 | `npm audit fix` |

---

## 5. Residual risks (stated, not fixed)

1. **No penetration test.** No manual adversarial testing, no external
   review, no bug bounty. This pass is static analysis, dependency
   scanning, and authorisation tests only.
2. **Rate limiting covers auth only.** All nine `@limiter.limit`
   decorators are in `auth_routes.py`. Checkout, review creation, review
   reporting, cart mutations, product/store writes, the notifications
   endpoints and `GET /api/exchange-rates` are **unthrottled**. The
   limiter storage is `memory://` — per-process, so it does not hold
   across multiple workers (ADR 0009 already notes this).
3. **`PRAGMA foreign_keys` is OFF in development and production.** SQLite
   ignores every foreign-key clause without the per-connection pragma;
   CedarLink issues it only under `TestConfig` (ADR 0023). Foreign-key
   integrity is *tested* but not *enforced at runtime*. ORM cascades run;
   database-level `ON DELETE` actions do not. Moving to Postgres (ADR
   0032) makes this moot; on SQLite the fix is a one-line `connect` event
   listener in `create_app`, deliberately not made here because it changes
   deletion behaviour and needs its own review.
4. **No security response headers.** No HSTS, `X-Content-Type-Options`,
   `X-Frame-Options`, `Referrer-Policy` or CSP. TLS is assumed to be a
   proxy's job and is not enforced or asserted by the app.
5. **A09 is essentially unbuilt.** No audit log of authentication
   failures, lockouts, password resets, 2FA changes, or admin actions; no
   alerting on anything. Correlation-id'd 500 logs and a handful of
   lifecycle `INFO` lines are the whole of it.
6. **The review-rating aggregate is race-safe on SQLite only.** An
   unlocked `SELECT avg,count` then a separate `UPDATE products` — SQLite
   serialises writers so it is exact, an MVCC database would let a
   concurrent writer store a stale count (ADR 0032 §4).
7. **`database is locked` under load is not retried.** ~100 concurrent
   checkouts produce a small fraction of generic 500s (contained, no
   leak) with no backoff or circuit breaker (ADR 0032 §3).
8. **Committed key material.** `config._PLACEHOLDER_FERNET_KEY` is a real
   Fernet key string in the repo. Used only under `TestConfig`;
   `ProdConfig` requires `TWO_FACTOR_ENCRYPTION_KEY` from the environment.
   Still a smell; there is no rotation story for that key.
9. **Registration still leaks email existence on one path** — `PUT
   /api/users/<id>` returns "Email already exists" when changing your own
   email to a taken one. Authenticated, own-account only, low value.
10. **Payment webhook secret is compared with `!=`**, not a constant-time
    comparison (`app/routes/payment_routes.py`) — a timing side channel on
    a secret. The endpoint fails closed if `PAYMENT_WEBHOOK_SECRET` is
    unset and nothing in the app currently calls the payment flow
    (ADR 0024), so this is low priority but real.

---

## 6. Consequences

- Three CI gates added; `requirements.txt` gains `bandit`, `pip-audit`,
  and a `pytest` bump; `package-lock.json` gains the `nanoid` bump.
- `tests/security/` — 13 tests, ~6 s, part of the suite.
- `docs/security/owasp-top-10.md` is the living map; this ADR is the
  point-in-time record.
- Six fixes shipped (table §4). Ten residual risks logged (§5) as the
  security backlog — items 3, 4, 5 and 10 are the next concrete pieces of
  work.
