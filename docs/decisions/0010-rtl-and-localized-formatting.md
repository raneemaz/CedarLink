# 0010 — RTL layout and localized date/number formatting

**Date:** 2026-08-30
**Status:** accepted
**Queue item:** 5 (C.5, first half — RTL sweep)

The i18n scaffolding (en/ar/fr JSON, `i18n.js`, `users.language`) already
existed. This item is the layout half: make the interface flip to
right-to-left in Arabic with no broken layout.

## Document direction

`i18n.js` owns `<html dir>` / `<html lang>`. It sets them at init and
re-applies on every `languageChanged` event — not only while the Language
screen is mounted, which was the old behaviour. `index.html` runs the same
detection inline in `<head>` so a hard reload in Arabic paints RTL from the
first frame with no left-to-right flash.

**First-visit detection**: with no saved preference, the language is taken
from `navigator.languages` (first of en/ar/fr, else English) and persisted.
Any later explicit choice on the Settings screen wins from then on.

Language persistence is `localStorage` only. The backend has
`users.language` and a `PUT /users/<id>/language`, but nothing reads it on
login yet — wiring that (the way `CurrencyContext` already loads
`users.currency`) is a small follow-up, not part of the layout sweep.

## The sweep

Physical Tailwind utilities → logical, judged case by case:

| From | To | Where |
|---|---|---|
| `text-left` / `text-right` | `text-start` / `text-end` | table headers, list-item buttons, the cart line total |
| `pl-` / `pr-` / `ml-` | `ps-` / `pe-` / `ms-` | list indent, the password-field inset, the page-size input |
| `absolute right-*` | `end-*` | dropdown menus, the password eye toggle, the image delete button |
| `-right-2` | `-end-2` | the cart / notification count badges |

`flex` rows, `gap-*`, `justify-between` and `space-*` were left alone —
they already reverse under `dir="rtl"`.

## Directional icons

A shared `<BackLink>` replaces ~20 hand-rolled "back to X" links. The arrow
is a lucide `<ArrowLeft>` with `rtl:rotate-180`, not a literal `←` glyph
(which the bidi algorithm does not mirror). Same treatment for the Settings
row chevron and the console "Back to CedarLink" arrows. Non-directional
icons — cart, bell, search, user — are untouched.

## Money and dates in an RTL paragraph

`Intl` output embedded in RTL text gets reordered: `"US$ 3.50"` renders as
`"$US 3.50"`, `"30/08/2026"` as `"2026/08/30"`.

- **`Price`** wraps its value in `dir="ltr"`.
- **`formatDate` / `formatDateTime`** use a spelled-out month
  (`30 أغسطس 2026`) instead of a slash-numeric date, which removes the
  ambiguity entirely.

### Arabic-Indic vs Western digits — decided

**Western digits (0–9) everywhere, Arabic included.** `formattingLocale`
maps `ar` → `ar-u-nu-latn`: Arabic month and day names, Arabic number
grouping, but Latin digits. Prices, quantities, phone numbers and order
IDs in Lebanese commerce are written in Western digits; mixing digit
systems across one screen would be worse than either alone.

### Transactional amounts

Cart, checkout, order and admin-total money stays a fixed `$X.XX` string.
Those amounts are contractual (what the customer is charged), always USD,
and a stable universally-legible format matters there more than
locale-matching. The **browsing** surface (`Price`) does use the active
locale, because that is discovery context. A future pass could add
thousands-grouping to the large admin totals.

## Mobile navbar

Pre-existing bug surfaced during verification (broke in both directions):
the login/register buttons, profile dropdown and logout button had no `lg:`
visibility gate, so on mobile they overflowed the bar and clipped the logo.
They are desktop-only now; the mobile bar is logo + cart + hamburger, and
every action lives in the drawer, which mirrors correctly in Arabic.

## Verified

Every screen in the item-5 checklist was checked in Arabic: navbar and
mobile drawer, product grid and filters, product detail, cart, checkout,
order history and detail, all Settings pages, the full vendor console, the
full admin console, login, register, forgot/reset password, 404. Layout
mirrors correctly with no overlap.

Residual (not layout breaks): pages that are not yet translated — Login,
Register, ForgotPassword, Products, parts of the vendor/admin consoles —
show leading English punctuation drifting to the front of a line
(`"?Forgot Your Password"`). This is bidi resolution of a Latin sentence in
an RTL block and disappears when the string is translated to Arabic, which
is the second half of C.5.
