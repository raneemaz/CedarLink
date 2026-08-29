# 0002 — Password reset

**Date:** 2026-08-29
**Status:** accepted
**Queue item:** 1 (completes it)

## Context

CedarLink had no password reset. A login system without one is the first
thing anyone tries to break, and it is a stated User Management requirement.
The app already sends 6-digit codes for registration and login through
`app/services/two_factor_service.py`.

## Decision

### Reuse the challenge flow

Password reset is a new `password_reset` purpose on the existing
`TwoFactorChallenge` machinery, not a new mechanism:

- `_create_delivery_challenge` / `_get_active_challenge` /
  `_record_failed_attempt` give us TTL, the attempt cap, the resend
  cooldown counters, hashed-code storage (`generate_password_hash`, never
  the code itself), and single-invalidation of prior challenges for free.
- A distinct purpose string means a reset code can never be replayed
  against the login or setup endpoints, and vice versa. `purpose` is a
  plain `String(30)` with no enum or CHECK, so no migration is needed.
- On success the challenge is marked `consumed_at` — single use.
- `reset_password` re-checks `deleted_at is None and is_active` before
  writing the new hash, so a challenge issued to an account that is later
  deactivated or deleted still cannot reset it.
- New password is stored with `generate_password_hash` and must be at
  least 8 characters.

Building a parallel token table would have duplicated all of the above and
given us a second thing to keep correct.

### Neutral request response

`POST /auth/password-reset/request` returns the **same** body —
`{ message, challenge_token, method }` — whether or not the email belongs
to a real account:

- A registered, resettable account gets a real challenge and an emailed
  code.
- Any other email gets a decoy `challenge_token` (`secrets.token_urlsafe`)
  that matches no challenge; confirming against it fails with the same
  generic "challenge is invalid or expired" error as a real expired token.

The endpoint therefore cannot be used to enumerate accounts. The
verification code only ever reaches a mailbox behind a real account.

Registration still leaks account existence through "Email already exists".
That is a known gap, left as-is for now per the task scope.

## Consequences / known gaps

- **No rate limiting** on `/password-reset/request` or `/confirm`, and the
  real-vs-decoy paths differ in timing (a real request sends an email).
  Enumeration is possible under a timing attack, and the request endpoint
  can be used to spam a mailbox. Rate limiting is **queue item 4**.
- **No token revocation.** A successful reset does not invalidate existing
  access or refresh tokens, so a session opened before the reset survives
  it. Token denylist / revoke-on-password-change is **queue item 4**
  (CL-09).
- Reset always uses email, regardless of the account's 2FA method. Codes
  go out through the same `MAIL_*` path as registration.
