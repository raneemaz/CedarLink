# 0005 — Vendor self-registration + store approval gate

**Date:** 2026-08-29
**Status:** accepted
**Queue item:** 3 (pulls the approval gate forward from C.1)

## Context

Vendors could only exist if an admin created the account out of band —
there was no `flask create-vendor` and `Register.jsx` hardcoded
`role: "customer"`. That does not scale past the demo: the plan's most
realistic early-vendor channel is Instagram sellers signing themselves up.

At the same time, the requirements say an admin approves stores, and today
anyone who could get a vendor account can list products that customers see
instantly.

## Decision

**Self-registration, gated at the store — not at the account.**

- `Register.jsx` asks "I want to shop / I want to sell" as the first
  choice and sends `role: "vendor"` for sellers. The server's existing
  `PUBLIC_REGISTRATION_ROLES = ("customer", "vendor")` allow-list is the
  real guard; `admin` stays CLI-only.
- A new vendor is a full account immediately: they verify their email,
  land on the store-creation form, create a store, and add products.
- `Store.approval_status` (`pending` | `approved` | `rejected`) +
  `Store.approval_note`. New stores start `pending`.
- The single storefront gate `Store.is_visible` now requires
  `approval_status == "approved"` on top of active-and-not-removed. The
  three query-level filters that mirror it (product list, product detail,
  store list) were updated to match.
- The vendor console is **not** blocked while pending — the vendor sees an
  "awaiting approval" banner and can keep working. Their store and products
  simply do not appear on the storefront yet.
- `PATCH /api/admin/stores/<id>/approve` and `/reject` (optional `note`).
  The admin Stores tab filters to pending and reuses `ConfirmDialog`.

### Why not admin-created vendor accounts

- It puts a human in the loop for every signup, which kills the
  self-serve funnel the business depends on.
- The risk it guards against — a bad actor listing junk — is better
  handled at the store level, where an admin reviews an actual store with
  a name, description and products, than at the account level, where there
  is nothing to review yet.
- Account creation and store approval are different concerns. Coupling
  them means a rejected store also destroys a usable customer account.

### Why grandfather existing stores to "approved"

The migration runs `UPDATE stores SET approval_status = 'approved'`. Every
store that predates this feature was already live; flipping them to
`pending` would silently pull the whole demo storefront down. Seed stores
are also created `approved` for fresh installs.

## Consequences / known gaps

- No email to the vendor on approve/reject yet — they find out by opening
  the console. `notification_service` could carry this later.
- A rejected store can be re-approved by an admin but the vendor has no
  "resubmit" action; they would ask an admin directly.
- Approval is all-or-nothing; there is no partial / conditional approval.
