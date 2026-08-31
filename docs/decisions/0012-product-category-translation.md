# 0012 — Product and category translation

**Date:** 2026-08-31
**Status:** accepted
**Queue item:** 11 (C.5, second half — product translation UI)

[0011](0011-ui-string-coverage.md) translated the interface chrome.
Catalogue *content* — product and category names and descriptions — was
still single-language: each row had one `name` column, despite `CLAUDE.md`
claiming `name_en` / `name_ar` / `name_fr`. This makes the schema match
that claim and gives vendors and admins a way to fill the translations in.

## Columns, not a translations table

`Product` gains `name_en` / `name_ar` / `name_fr` and
`description_en` / `description_ar` / `description_fr`; `Category` gains
`name_en` / `name_ar` / `name_fr` (its `description` stays single-language —
it is not shown prominently and nothing asked for it).

Three fixed languages, forever — the app is `en` / `ar` / `fr` and that set
is not user-extensible. A key–value `translations(entity, field, lang)`
table would buy flexibility we will never use and cost us:

- **Sorting and searching stay plain SQL.** `ORDER BY name_en`, and a
  keyword `ILIKE` across six columns, need no joins or `GROUP BY`.
- **The serializer is a dict literal**, not a query per row.
- **A missing translation is `NULL` in a column**, trivially
  `COALESCE`-able, rather than an absent row to `LEFT JOIN`.

The cost is three migrations if a fourth language is ever added. That trade
is clearly right at this size.

## English is the required base

`name_en` is `NOT NULL`; `name_ar` / `name_fr` (and every `description_*`)
are nullable. Resolution is **fall back to English, never blank**:

```
localized_name(lang) = name_{lang} if non-blank else name_en
```

`name_en` cannot be blank, so a product name is always renderable. A
whitespace-only translation counts as missing. The vendor and admin forms
enforce a non-empty English value client- and server-side.

## `.name` / `.description` are synonyms

`Product.name = db.synonym("name_en")` (same for `description`, and
`Category.name`). Every existing query, factory, log line and error message
that said `product.name` keeps working against the English column —
including `Product.name.ilike(...)` and `filter_by(name=...)`. This kept the
migration's blast radius to the display layer: the 64-test suite passed
untouched. Display code calls `localized_name(lang)` explicitly.

## The API returns everything; the client picks

Serializers (`/products`, `/products/<id>`, `/categories`, cart items,
order items) return `name_en` / `name_ar` / `name_fr` (and the `_en` value
again as a bare `name` alias for any not-yet-language-aware consumer). The
server **does not** read `Accept-Language` or a `?lang=` param. The client
already knows the active language, so switching it re-renders instantly with
no refetch. `frontend/src/utils/localize.ts` is the single picker.

## Search covers all six columns

`GET /products?keyword=` matches `name_{en,ar,fr}` and
`description_{en,ar,fr}` with `OR ... ILIKE '%kw%'`. A customer searching in
Arabic finds a product whose Arabic name matches whatever the interface
language is.

**Known limitation:** this is substring `ILIKE`. It does not fold Arabic
diacritics, does not stem, and cannot rank. The plan (§C.5) calls for
Postgres full-text search with an Arabic configuration once the database
moves off SQLite (deployment, queue item 16); on SQLite the alternative is a
normalized shadow search column written on save. Neither is built here —
matching the right column is the requirement for this item; quality of the
match is future work.

## Migration `c5a1b2d3e4f7`

SQLite batch mode. Adds the `_ar` / `_fr` columns nullable, then renames
`name` → `name_en` and `description` → `description_en`. The rename carries
every existing row's value across, so there is no backfill statement and
nothing is lost; the `UNIQUE (name_en)` and
`CHECK (stock >= 0)` constraints survive the table recreate. Downgrade
reverses the renames and drops the added columns (translation values
entered after the upgrade are lost on downgrade — acceptable). Verified on a
fresh database: upgrade → insert rows → downgrade → re-upgrade, schema and
data intact each way.

## Seed

`flask seed` now carries real Arabic and French for all 5 categories and 20
products, and backfills them onto rows that predate the migration, so the
demo catalogue is genuinely trilingual and the command stays idempotent.

## UI

`LanguageTabs` — an `en` / `ar` / `fr` tab bar with a filled-dot indicator
per optional language and a required mark on English. The vendor product
form puts name and description behind it (one language at a time); the admin
category form does the same for the name. A validation error on the English
name snaps the form back to the English tab so it is visible.

## Verification

`npm run lint` (0 errors), `npm run build`, and `pytest` (72 passing, +8
new) all green. Manual pass in all three languages: a product created with
three names shows each correctly on the card, the detail page, the cart and
the order; a product with no French shows English on the French UI, not a
blank; Arabic keyword search finds an Arabic-named product from an English
session.
