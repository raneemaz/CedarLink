# 0008 — JWT revocation

**Date:** 2026-08-30
**Status:** accepted
**Queue item:** 4, session 4 (security hardening — CL-09)

## Context

Access tokens live 15 minutes and were never checked against anything.
Consequences:

- An admin suspends an abusive user; the user keeps ordering, messaging and
  editing for up to 15 minutes on the token they already hold.
- "Logout" only cleared `localStorage`. A token copied out of the browser
  stays valid until it expires.
- A password reset did not invalidate sessions — a stolen token outlived
  the password it rode in on.

## Decision

Two mechanisms, one check.

### Individual revocation — `token_denylist`

`TokenDenylist(jti, token_type, user_id, created_at, expires_at)`. Logout
inserts the current token's `jti`; if the client sends its refresh token in
the body, that `jti` goes in too. `expires_at` lets a future cron prune
rows that can no longer matter.

### Bulk revocation — `User.tokens_revoked_at`

You cannot enumerate a user's outstanding tokens, so bulk revocation cannot
work by inserting denylist rows. Instead a per-user cutoff: any token whose
`iat` predates `tokens_revoked_at` is dead. Stamped on:

- **password reset** (`two_factor_service.reset_password`)
- **admin suspension** (`admin_routes.suspend_user`)
- **self-deactivation** (`account_service.deactivate_account`)

### The check

`token_service.register_jwt_callbacks` installs
`@jwt.token_in_blocklist_loader`. On every `@jwt_required` request it looks
up the `jti` in `token_denylist`, then compares the token `iat` to the
user's `tokens_revoked_at`. Two indexed point-lookups; acceptable for this
scale. A suspended user's live token is rejected on their **next request**.

`tokens_revoked_at` is naive UTC to match the integer `iat`
(`datetime.fromtimestamp(iat, utc)` floored to naive). `iat` floors down to
the second and the cutoff is always strictly after the real issue time, so
a freshly issued token is never caught by its own revocation.

## Alternatives considered

- **Denylist only, no per-user cutoff.** Cannot express "revoke everything"
  without tracking every issued token.
- **Short access tokens + always hit the DB.** Already effectively what the
  blocklist loader does; the 15-minute expiry stays as defence in depth.
- **Refresh-token rotation.** Worth doing later; out of scope here. Logout
  revokes the refresh token it is given, which closes the immediate gap.

## Consequences

- Every authenticated request now does up to two extra SELECTs. Fine at
  this scale; revisit with caching if it ever isn't.
- `token_denylist` grows by one row per logout. A prune job (delete where
  `expires_at < now`) is a follow-up, not a blocker.
- Tests: `tests/integration/test_token_revocation.py`.
