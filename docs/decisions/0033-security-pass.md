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
| A01 Broken Access Control | Strong; enumerated tests. One missing guard fixed (first pass). |
| A02 Security Misconfiguration | Headers **fixed** (§5a), `PRAGMA foreign_keys` **fixed** (§5a). Still: CSP by decision, CORS default is dev-local. |
| A03 Software Supply Chain | Gated (bandit / pip-audit / npm audit). No SBOM / provenance / hash-pinning. |
| A04 Cryptographic Failures | Strong (scrypt, Fernet, no card data). Committed Fernet key **fixed** (§5a). Still: no app-level HSTS enforcement beyond the header; no key rotation story. |
| A05 Injection | Strong. ORM throughout; one guarded raw-SQL constant. |
| A06 Insecure Design | Strong on the recorded decisions. **No formal threat model doc.** |
| A07 Authentication Failures | Strong (2FA, enumeration resistance). Password floor + abuse-path rate limiting + `PUT /users` enum leak all **fixed**. Still: no complexity / breach check, no refresh rotation. |
| A08 Software/Data Integrity | Migration-drift gate; recompute-not-increment. Review aggregate now atomic — **fixed** (§5a #6). |
| A09 Security Logging & Alerting | **Largely unaddressed.** 13 log calls in `app/`; no audit log; no alerting. The one category this pass did not move. |
| A10 Mishandling Exceptional Conditions | Strong containment. `database is locked` retry on checkout **fixed** (§5a #7); the SQLite write ceiling itself remains (ADR 0032). |

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

## 5. Residual risks

### 5a. Follow-up pass — 2026-09-07 (commits `ecb3921`…`aec70cf`)

A ten-item punch list. Seven of the ten residual risks below (§5b) are
now closed; the numbering is preserved so the original claim stays
visible next to its fix.

| # | Was | Change | Proof |
|---|---|---|---|
| 2 | rate limiting was auth-only | `@limiter.limit` (per user, IP fallback) on `POST /api/cart/coupon` (10/min, 40/hour — the /hour cap is the coupon-enumeration guard), `POST /api/orders` (8/min, 30/hour), `POST /api/reviews` (6/min, 20/hour), review report (10/min, 30/hour). `app/utils/rate_limit.user_or_ip_key`. | `tests/security/test_rate_limits.py` (4) |
| 3 | `PRAGMA foreign_keys` OFF in dev/prod | `Engine.connect` listener moved from `conftest.py` into `app/extensions.py` — fires in every config. Full suite: 509 pass, **0 new failures** (the suite already ran with FK on, so any cascade that relied on FK-off would already have failed). `flask seed` / `--reset` verified. | 509-test run + `flask seed` |
| 4 | no security headers | `after_request`: `X-Content-Type-Options: nosniff`, `X-Frame-Options: DENY`, `Referrer-Policy: strict-origin-when-cross-origin`, and HSTS only when `request.is_secure` (inert on dev http, correct behind a TLS proxy — ProxyFix already trusts `X-Forwarded-Proto`). **CSP is deliberately still absent** — the pre-paint inline theme script in `frontend/index.html` needs a nonce or hash to survive a real policy, which is its own piece of work. | `tests/security/test_security_headers.py` (5) |
| 6 | review aggregate race-safe on SQLite only | `review_service._recalculate_rating` is now one `UPDATE …/stores SET rating_count = (SELECT count()…), rating_avg = (SELECT round(avg(),2)…) WHERE id = :id`. Ports to Postgres unchanged (ADR 0032 §4). | `tests/integration/test_rating_recompute_atomic.py` (3) — asserts exactly one statement |
| 7 | `database is locked` not retried | `app/utils/db_retry.with_write_retry` around the checkout call only — on that specific error, roll back, back off 50/100 ms, retry (3 total). `scripts/loadtest.py` N=100 checkout: **before** 0,1,2,2,3,5 failures / 6 runs → **after** 0,0,0,0,0 / 5 runs. Throughput unchanged. | `tests/unit/test_db_retry.py` (4) + loadtest re-run |
| 8 | committed Fernet key | `config._PLACEHOLDER_FERNET_KEY` deleted. `TestConfig.TWO_FACTOR_ENCRYPTION_KEY` falls back to `Fernet.generate_key()` — a fresh key per test process, never in the diff. `ProdConfig` unchanged (env-required). | existing 2FA suite (~25) still green |
| 9 | email-existence leak on `PUT /api/users/<id>` | Matches the decoy-success pattern registration uses: name/phone update as before, the email changes only when new **and** free, response byte-for-byte identical either way, body echoes the true stored email. | `tests/security/test_email_enumeration.py` (3) |
| 10 | webhook secret compared with `!=` | `hmac.compare_digest`, matching the TOTP check in `two_factor_service.py`. Still fails closed when `PAYMENT_WEBHOOK_SECRET` is unset. | `tests/security/test_payment_webhook_secret.py` (4) |

`bandit -r app/ -ll` still clean after all of this; `pip-audit -r
requirements.txt` clean (`bandit`, `pip-audit` are pinned; `bandit` also
lints the two new `# nosec`-free util modules).

### 5b. Still open

1. **No penetration test.** No manual adversarial testing, no external
   review, no bug bounty. This work is static analysis, dependency
   scanning, and authorisation / abuse-path tests only.
2. *(fixed — §5a #2)* — **narrower residual:** cart *item* mutations,
   the notifications endpoints and `GET /api/exchange-rates` are still
   unthrottled (deliberately — a cart edit is idempotent-ish, notifications
   are self-scoped reads/marks, and the exchange rate is served from an
   in-process cache so hammering it does not reach the upstream). The
   limiter storage is still `memory://` — per-process, needs a shared
   backend for multiple workers (ADR 0009).
3. *(fixed — §5a #3)*
4. *(fixed — §5a #4)* — **CSP is still not set**, by decision (see the
   table). That is the one header of the standard set CedarLink does not
   send.
5. **A09 (Security Logging and Alerting) is essentially unbuilt.** No
   audit log of authentication failures, lockouts, password resets, 2FA
   changes, or admin actions; no alerting on anything. Correlation-id'd
   500 logs and a handful of lifecycle `INFO` lines are the whole of it.
   This is the largest remaining gap and needs a project of its own — a
   structured audit-event sink, an append-only store, threshold alerts on
   auth-failure and 5xx rate.
6. *(fixed — §5a #6)*
7. *(fixed — §5a #7)* — the retry masks the SQLite single-writer ceiling,
   it does not lift it (~12 write/s; ADR 0032). WAL roughly doubles it
   (measured, ADR 0032) but the app's `journal_mode` default is unchanged.
8. *(fixed — §5a #8)* — no rotation story for the production
   `TWO_FACTOR_ENCRYPTION_KEY` (rotating it makes every stored TOTP secret
   undecryptable). Roadmap.
9. *(fixed — §5a #9)*
10. *(fixed — §5a #10)* — the payment flow is still not wired up at all
    (ADR 0024); when it is, the webhook needs a real signature scheme
    (HMAC of the body), not just a shared bearer secret.
11. **`token_denylist` has no cleanup job.** Measured (ADR 0032): 100,000
    expired rows add **0 ms** to the per-request blocklist lookup (covering
    index, O(log n)), so this is storage tidiness, not a performance
    finding. A periodic `DELETE … WHERE expires_at < now()` is roadmap.

---

## 6. Consequences

- Three CI gates added; `requirements.txt` gains `bandit`, `pip-audit`,
  and a `pytest` bump; `package-lock.json` gains the `nanoid` bump.
- `tests/security/` — now 32 tests (13 in the first pass, 19 in the
  follow-up), part of the suite.
- `docs/security/owasp-top-10.md` is the living map; this ADR is the
  point-in-time record.
- **First pass:** six fixes (table §4), ten residual risks (§5).
- **Follow-up pass (§5a):** seven of the ten residual risks closed, plus
  the scale fixes in ADR 0032. What is left (§5b): no penetration test
  (#1), A09 unbuilt (#5), CSP by decision (#4), a narrower rate-limit gap
  (#2), and three roadmap items (#8 key rotation, #10 real webhook
  signatures, #11 denylist cleanup). **A09 is the one that needs a
  project, not a patch.**
