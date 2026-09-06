# 0031 — Privacy Policy and Terms of Service

**Date:** 2026-09-06
**Status:** accepted

Two public pages — `/privacy-policy` and `/terms` — linked from the footer
and from the registration form, in all three locales, both themes, RTL
correct. Both are marked as academic documents produced for a university
project and not legal advice.

## The privacy policy is derived from the schema, not a template

The requirement was to walk `app/models/` and enumerate every column that
holds personal data, then write the policy from that enumeration. The
result:

| Where | Fields | Purpose | Seen by | Retention |
|---|---|---|---|---|
| `users` | `first_name`, `last_name`, `email`, `phone` | account, sign-in, order contact, notices | self; vendor (name + phone, own-store orders only); admin | life of the account; anonymised on delete |
| `users` | `language`, `currency`, `theme` | UI preferences | self; admin | until changed / delete |
| `users` | `password` (hash), `two_factor_*`, `two_factor_totp_secret` (Fernet-encrypted), `verification_method` | account security | no one — never displayed | life of the account |
| `users` | `is_active`, `suspended_at`, `suspension_reason`, `deleted_at`, `tokens_revoked_at` | lifecycle / moderation state | self (own status); admin | life of the row |
| `addresses` | `label`, `recipient_name`, `phone`, `address_line`, `city`, `delivery_instructions`, `latitude`, `longitude` | delivery, checkout pre-fill | self; vendor + driver for an order to that address | until address or account deleted |
| `orders` | `delivery_address`, `delivery_city`, items, prices, `delivery_fee`, status | fulfilment, order history, sales record | self; order's vendor; admin | kept after account deletion as financial record; `delivery_address` scrubbed to `[deleted]` |
| `payment_methods` | `brand`, `last4`, `exp_month`, `exp_year`, `label` | tell saved cards apart | self only | until card or account removed |
| `payment_methods` | `provider`, `provider_customer_id`, `provider_payment_method_id` | forward-looking tokenisation fields (ADR 0024) | — | empty today |
| `payments` | `amount`, `method`, `provider`, `provider_payment_id`, `transaction_id` | order settlement record | self; vendor; admin | with the order |
| `reviews` | `rating`, `title`, `body`, `user_id`, `order_id` | verified-purchase reviews | public sees rating/title/body + author **first name only** (ADR 0019); admin sees full identity | outlives product/store; kept, re-attributed to "Deleted", after account deletion |
| `review_reports` | `reason`, `user_id` | moderation evidence | admin | kept as evidence (ADR 0017) |
| `delivery_assignments` | `driver_name`, `driver_phone` | driver coordination | vendor always; customer only while status ≠ `delivered` (ADR 0019) | with the order |
| `notification_preferences` | category + channel toggles | notification routing | self; admin | until changed / delete |
| `notifications` | `title`, `message`, `link` (contain order facts) | in-app notices | self | until account deletion (purged) |
| `shopping_preferences` | `autofill_default_address`, `preferred_payment_method`, `default_delivery_city`, `hide_out_of_stock` | checkout convenience | self | until changed / delete |
| `shopping_interests` | `category_id`, `position` | **stated** interests only, never inferred (ADR 0022) | self; admin ("who likes X" query) | until changed / delete |
| `carts` / `cart_items` | `coupon_code`, product + quantity | the working cart | self | until account deletion (purged) |
| `two_factor_challenges`, `two_factor_recovery_codes`, `token_denylist` | hashes, expiries, `jti` | sign-in, step-up auth, logout | no one — hashes only | see finding 2 |

Non-personal tables (`stores`, `products`, `categories`, `store_hours`,
`store_announcements`, `store_social_links`, `product_images`, `coupons`,
`coupon_redemptions`) hold vendor/catalogue data. A vendor's
`store.contact_info` and social links are personal data the vendor chooses
to publish; the policy notes them as vendor-controlled and public.

**No column stores an IP address or device fingerprint.** `flask-limiter`
keys on the remote address for rate-limiting, but the store is `memory://`
— the value is never written to the database. The policy says so.

### Findings

1. **Portability is not implemented, and the brief's premise was slightly
   off.** `/settings/privacy` (`PrivacyData.jsx`) offers **deactivate** and
   **delete** — not export. Law 81/2018 lists portability alongside access,
   correction and deletion; CedarLink does the other three (account pages;
   Privacy & data page) but has no "download my data" control. The policy
   states this plainly rather than implying a right that isn't wired up,
   and links only the controls that exist. An export endpoint is roadmap.

2. **Security-housekeeping rows are never pruned.** `two_factor_challenges`,
   `two_factor_recovery_codes` and `token_denylist` all carry an
   `expires_at` "for a cleanup job", but no such job exists — rows
   accumulate for the life of the database. They hold only hashes and
   timestamps, so this is hygiene, not exposure; the policy describes them
   as "expire quickly" in the sense that they stop being *usable* quickly,
   which is true. A prune command is roadmap.

3. Every other column maps to a purpose a user would expect. Nothing was
   found that could not be justified.

## What deletion actually does (so the policy can be accurate)

`account_service.delete_account` is anonymise-in-place, not erasure:
addresses, cards, notifications, preferences, 2FA material and the cart are
hard-deleted; the `users` row is kept (orders FK it `NOT NULL`) with name,
email and phone replaced; past orders keep their rows with
`delivery_address` scrubbed; reviews stay, shown as by "Deleted". Deletion
is blocked while an order is in progress. The policy's deletion section is
written from this function.

## Terms of Service

Plain language, no borrowed boilerplate. Covers: marketplace-not-seller;
account rules; customer and vendor obligations; one-order-per-store and
single-pricing-path; cash on delivery as the only settlement (and that a
saved card moves no money — ADR 0024); cancellation restoring stock and
reversing coupons; coupon limits and the multi-store fixed-coupon rule
(ADR 0021); delivery fees as a pass-through to the driver; review
moderation and the six grounds for removal (ADR 0017); admin suspension
vs self-deactivation; "as is" availability; limitation of liability;
Lebanon as the operating context.

## Mechanics

- **One "last updated" date.** `frontend/src/pages/legal/legalMeta.js`
  exports `LEGAL_LAST_UPDATED` (a plain `YYYY-MM-DD`) and
  `LEGAL_LAST_UPDATED_ISO` (the same pinned to noon UTC so the rendered day
  is timezone-stable). Both pages import it; it is never typed into a
  translation file. A test asserts it is one real date.
- **Shared shell.** `LegalDocument.jsx` renders the back link, the academic
  notice, the title, the date, the intro and a list of titled sections for
  both pages. Section bodies are plain translated strings; a blank line
  starts a paragraph and a block of `- ` lines becomes a bullet list. The
  privacy page additionally passes the six account-control links, rendered
  after the contact section.
- **Translations.** New namespaces `privacyPolicy`, `terms`, `footer` and
  one `register.agreeToTerms` key, added to `en` / `ar` / `fr` with real
  translations (not placeholders). The registration line uses `<Trans>` so
  the two inline links survive reordering in Arabic and French. A parity
  check (plural suffixes collapsed) confirms identical key sets across the
  three files.
- **Tokens.** Both pages use only role tokens; `npm run lint:tokens`
  passes. No `index.css` change, so the contrast gate is untouched and
  `KNOWN_FAILURES` stays empty.

## Verification

- 480 backend tests pass; frontend `node --test` 13 → 19 (6 new).
- `npm run lint` 0 errors / 17 warnings; `npm run build` passes.
- `lint:tokens` green; contrast gate green (0 known failures).
- Rendered `/privacy-policy` and `/terms` in en, and `/terms` in Arabic:
  `dir=rtl`, `text-align: start`, `padding-inline-start` on lists, dark
  palette (`--color-paper` `oklch(21%…)`, `--color-ink` `oklch(93%…)`).
  Registration shows the agree line with `/terms` and `/privacy-policy`
  links; footer links both pages.

## Not done (roadmap)

- A data-export / portability endpoint and its `/settings/privacy` control.
- A prune command for expired `two_factor_challenges` /
  `two_factor_recovery_codes` / `token_denylist` rows.
- A real contact address (the documents use `@cedarlink.example`
  placeholders and say so).
