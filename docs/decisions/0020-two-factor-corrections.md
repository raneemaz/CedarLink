# 0020 — Two-factor and password-reset corrections

**Date:** 2026-09-03
**Status:** accepted
**Queue item:** authentication test coverage (follow-up fixes)

The previous session wrote the first tests for the two untested
authentication paths — password reset and 2FA — under a standing
instruction to **report defects rather than fix them**. Four tests failed
because the production behaviour was wrong. They were committed as
`xfail(strict=True)` so the suite stayed green while the gaps stayed
visible, and `strict` meant each one was *confirmed*, not suspected: a
strict xfail that starts passing is itself a failure.

This ADR records what they were, why #2 is the serious one, why #1 and #2
are coupled, and the decisions taken in fixing them. Each fix removed its
marker in the same commit, so every test went from failing-as-expected to
passing-normally in one diff.

## How they were found

None of these came from reading the code hunting for bugs. They came from
writing down what the path is *supposed* to guarantee and asserting it:

- "a code cannot be replayed" → #1
- "confirming TOTP changes what login asks for" → #2
- "an account that may not reset is refused" → #3, #4

Two of the four (#1, #2) were visible on a careful read of
`two_factor_service.py` and were predicted before the tests ran. The
value of the tests was not discovery — it was **proof**, plus a marker
that fails the day the behaviour regresses. #2 in particular reads as
correct at a glance; only executing it shows that the branch order
matters.

## 1. A TOTP code could be replayed

`_verify_challenge_code` called `pyotp.TOTP(secret).verify(code,
valid_window=1)` and kept no record of what had been used.

Consuming the challenge on success is not sufficient. An attacker who
observes a code — over a shoulder, on a shared screen, in a screenshot —
can open a **fresh** login challenge and replay the code there. With
`valid_window=1` (one step either side of a 30-second step) that leaves a
window of up to ~90 seconds.

**RFC 6238 §5.2** is explicit:

> "The verifier MUST NOT accept the second attempt of the OTP after the
> successful validation has been issued for the first OTP, which ensures
> one-time only use of an OTP."

**Decision.** `User.two_factor_last_totp_counter` (Integer, nullable)
holds the highest time step the user has authenticated with. Any code
resolving to a step at or below it is refused.

`pyotp.verify()` returns only a boolean, so `_matching_totp_counter` walks
the same window `verify()` walks and compares each step's code with
`hmac.compare_digest`, returning the step that matched. This is the same
work `verify()` does internally; it exposes nothing extra.

A monotonic high-water mark, rather than a set of consumed codes, is what
makes this cheap: time steps only ever move forward, so one integer per
user replaces per-code bookkeeping — no table, no expiry job.

**The mark is not cleared when 2FA is disabled.** It could be, since the
column describes a credential that no longer exists, but keeping it is
strictly safer and costs nothing. If a user disables and re-enables TOTP
with a new secret, a stale mark refuses codes from steps already in the
past: a no-op after the first ~90 seconds, and it closes a window that
clearing the mark would open.

**Recovery codes were already correct.** `_consume_recovery_code` marks a
row `used`, and the tests confirm a code works exactly once. That path is
untouched.

## 2. Login asked for the wrong factor — the serious one

`create_login_challenge` tested `user.verification_method in
DELIVERY_METHODS` **before** `user.two_factor_enabled`.

The two fields answer different questions:

| field | means |
|---|---|
| `verification_method` | how the account was confirmed at registration |
| `two_factor_method` | the second factor the user chose |

`confirm_setup` sets the second but never rewrites the first. So the
**normal state after setting up an authenticator** was
`verification_method="email"` + `two_factor_method="totp"` — and login
took the first branch and emailed a one-time code.

This is the serious one, for three reasons:

1. **It is the default path, not an edge case.** Every user who set up
   TOTP was in this state. No configuration avoided it.
2. **It silently downgrades the factor.** The user believes they hold a
   possession factor bound to a device. They actually hold an emailed
   code, so the account's security collapses back to the security of the
   mailbox — which is usually the exact dependency 2FA is adopted to
   remove. Nothing in the UI said so.
3. **It was invisible from inside the app.** `GET /api/users/{id}/2fa`
   reports `two_factor_method: "totp"`, because it reads the field that
   *was* set correctly. The status endpoint and the login behaviour
   disagreed, and only login was telling the truth.

**Decision.** Test `two_factor_enabled` first. A configured second factor
wins; `verification_method` is the fallback for users who have none.

**No data migration.** Rows already in the broken state are covered by
precedence alone: the new branch reads `two_factor_enabled` and never
consults `verification_method`, so a legacy row is challenged by TOTP on
its next login with no backfill. A test builds exactly that row
(`verification_method="email"`, `two_factor_method="totp"`) and proves it,
rather than resting on the argument. A migration would have been write
amplification for no change in behaviour.

### Why #1 and #2 are coupled

They are the same weakness seen from two ends, and the order of the fixes
mattered.

Before #2 was fixed, almost every real login challenge was an **emailed**
code — verified by `check_password_hash` against `challenge.code_hash`
and bound to a single challenge row. Emailed codes were never replayable,
because the row is consumed. So #1, the TOTP replay, was largely
*latent*: the branch it lives in was barely being reached.

Fixing #2 routes real users down the TOTP branch for the first time. That
turns #1 from a defect in rarely-executed code into a defect on the hot
path. **#2 is what makes #1 worth fixing, and fixing #2 without #1 would
have been a net regression** — moving users off a factor that could not
be replayed and onto one that could.

Hence the order: #2 first, then #1, with #1 landing before either reaches
`main`.

## 3 & 4. `_account_can_reset` was too narrow

It checked `deleted_at` and `is_active` only, so a **suspended** account
could complete a password reset, and an account whose address was never
verified could be mailed a code.

Neither is a privilege escalation: `/api/auth/login` refuses suspended,
unverified, deleted and inactive accounts at 403 regardless of the
password, so a successful reset buys no session. They are still wrong. A
suspension is an admin decision and should reach every credential path,
and the platform should not send mail to an address whose ownership it
has never confirmed.

**Decision.** Add `user.suspended_at is None and user.is_verified`.

**The refusal must stay indistinguishable from success.** This is the
property that keeps the endpoint from becoming an **account-status
oracle** — otherwise an attacker could sort addresses into live,
suspended, unverified and unknown without ever attempting a login.
`request_password_reset` returns the same decoy payload for every
refusal, and `password_reset_request` projects the response down to a
fixed three keys (`message`, `challenge_token`, `method`), so the decoy
and the real payload cannot differ in shape even though
`_challenge_payload` carries an extra `expires_at` internally.

A parametrised test asserts this across all four refusal reasons: same
status, same keys, same message, same method; only the opaque token
differs, and no code is sent.

## Known cosmetic inconsistency: the attempt cap returns 400, not 429

`_get_active_challenge` raises `TwoFactorRateLimitError` (429) when
`attempt_count >= TWO_FACTOR_MAX_ATTEMPTS`. **That branch never fires for
the attempt cap.** `_record_failed_attempt` sets `consumed_at` at exactly
`TWO_FACTOR_MAX_ATTEMPTS`, so the next lookup — which filters on
`consumed_at=None` — does not find the row at all, and returns 400
"Verification challenge is invalid or has already been used".

**The cap works.** Five wrong guesses kill the challenge, and the tests
assert exactly that, including that the correct code no longer works
afterwards. Only the error *type* is never the one the code appears to
intend.

**Not fixed, deliberately.** Changing it means either dropping the
`consumed_at` write from `_record_failed_attempt` (leaving exhausted
challenges alive and relying solely on the count) or adding a second
lookup for consumed-and-exhausted rows to tell the two cases apart. Both
add a branch to a security path in order to improve a status code, and
400 is not a wrong answer — the challenge genuinely is unusable. Recorded
here so the next reader does not spend the time working out why the 429
never appears, and does not "fix" the cap by removing the `consumed_at`
write.

## Frontend

A backend fix that leaves the UI telling users to check an email that
will never arrive is not a fix. Before #2, every login challenge was an
emailed code, and `Login.jsx` assumed it: a prompt implying a delivered
code, and a **"Resend code"** button posting to `/auth/2fa/resend`.

The login screen now reads `method` off the challenge response and
branches:

- **`totp`** — its own prompt ("Enter the current code from your
  authenticator app"), and no resend control. There is nothing to resend:
  the code is generated on the device, and the request would have failed
  against a TOTP challenge anyway.
- **anything else** — the delivered-code prompt, now explicit that the
  code was emailed, with resend intact.

Strings added to `en/ar/fr` (`login.promptCodeTotp`, plus a reworded
`login.promptCode`). No new layout, so no RTL work beyond what the
existing card already handles.

## Consequences

- `users` gains one nullable integer column (migration `fa263630a9da`,
  verified up-from-empty, down, up, with `flask db check` clean).
- TOTP users are challenged by their authenticator from their next login,
  with no backfill and no re-enrolment.
- A user who authenticates twice inside one 30-second step is refused the
  second time. That is the intended behaviour and matches every other
  TOTP implementation, but it is worth knowing before someone reports it
  as a bug.
- Suspended and unverified accounts can no longer reset a password.
  Neither could log in either way, so no working flow is lost.
