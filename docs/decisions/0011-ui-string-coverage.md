# 0011 — UI string coverage (en / ar / fr)

**Date:** 2026-08-31
**Status:** accepted
**Queue item:** 5 (C.5, second half — string extraction)

[0010](0010-rtl-and-localized-formatting.md) made the layout flip to RTL
but left many screens rendering hardcoded English inside that layout. This
item extracts every user-visible string on those screens into the three
translation files with real Arabic and French, not English placeholders.

## Scope

Screens that had no (or partial) coverage, now done:

- Auth: Login, Register, RegisterVerify, ForgotPassword, ResetPassword
- Browsing: Products, ProductDetails, Stores, StoreDetails, Categories,
  ProductCard, Price tooltip
- Checkout flow: Cart, Checkout, Orders, OrderDetails
- Account: Profile, Saved Addresses, Payment Methods (list / add / edit),
  Security
- Vendor console: store, products, product form, image manager, orders
- Admin console: overview, users, stores, categories
- Shared: layouts, NotFound, ConfirmDialog, and toast / error strings
  throughout

`en.json` now holds ~936 leaf strings across 49 namespaces (`ar.json` has
more — see plurals below).

## Key conventions

- One namespace per screen, camelCase, matching the pre-existing structure
  (`vendorStore`, `adminUsers`, …).
- Vocabulary shared across screens gets its own namespace rather than being
  duplicated: `auth`, `backLink`, `orderStatus`, `deliveryStatus`, `role`,
  `userStatus`, `storeStatus`, `addresses`, `paymentMethods`, `common`.
- Toasts, empty states, table headers, button labels, placeholders and
  `aria-label` / `alt` / `title` attributes are all covered — not just body
  text.
- API error messages keep the `response.data.message || t("…")` shape: the
  backend string wins when present, the translated fallback covers network
  failures.

## Interpolation, never concatenation

Anything with a value in it uses an i18next variable so word order can
change per language:

- `t("productImages.usage", { count, max })` → "3 of 5 used" / "٣ من ٥
  مستخدمة"
- `t("adminUsers.dialogSuspendMessage", { email })`
- Prices and dates are pre-formatted by the caller and passed **as
  strings** into `{{price}}` / `{{date}}`, so the `$` and the digits stay
  put while the surrounding words translate.

Module-scope lookup tables that used to hold English (`DIALOG`,
`ORDER_NEXT_LABEL`, `validate()`'s error strings) were changed to hold
i18next **keys**; the component resolves them with `t()` at render.

## Pluralisation

Counts use i18next plural keys. English and French define `_one` / `_other`;
Arabic defines all six CLDR forms (`_zero _one _two _few _many _other`),
which is why `ar.json` has ~20 more leaf keys than `en.json`. Verified live:
`adminOverview.orderCount` renders "2 orders" (en), « 2 commandes » (fr) and
"طلبان" — the dual form — in Arabic.

## Keeping the three files in sync

A merge script (`scratchpad`, not committed) deep-merges new keys into all
three files and asserts identical key sets after collapsing plural
suffixes. Every batch ran through it, so a missing translation fails loudly
instead of shipping as a visible key.

## Verification

`npm run lint` (0 errors, 16 pre-existing warnings) and `npm run build`
pass. Each console was opened in all three languages: admin overview /
users / stores / categories and vendor store / products / orders render
fully translated with working interpolation and plurals, and the RTL
punctuation drift from 0010 is gone now that Arabic screens use native
« ؟ ».

## Not done (roadmap)

- Category and product **names** shown in these tables are user data from a
  single `name` column. The `name_en/_ar/_fr` split that `CLAUDE.md`
  describes is not implemented on `Product` / `Category` yet; that is
  backend work, out of scope for string extraction.
- `users.language` still isn't read on login (noted in 0010).
