# 0036 — Variant management and the customer picker (V-2)

**Date:** 2026-09-10
**Status:** accepted
**Queue item:** V-2 (follows V-1 / ADR 0035)

## Where V-1 left it

V-1 built the schema, the variant-aware pricing/stock split, and the
read-side serialization. A product with variants priced and checked out
correctly — but only if a `variant_id` was supplied, and nothing in the
site could supply one: no vendor screen to create an option axis or a
variant, no customer picker, and **no CRUD endpoint** for
`product_options` / `product_option_values` / `product_variants` anywhere.
V-2 is that management layer plus the three UI surfaces.

## Part A — the endpoints

Ten routes under a new blueprint `product_variant_bp`
(`app/routes/product_variant_routes.py`), all `url_prefix="/api"`, behind
the business layer in `app/services/product_variant_service.py`. Each route
loads the product, checks the caller owns its store (or is an admin) — the
same gate `product_routes.update_product` uses — and returns the refreshed
`variant_fields(product, include_inactive=True)` so the vendor UI repaints
from the response.

| Method | Path |
|---|---|
| POST | `/api/products/<id>/options` |
| PUT · DELETE | `/api/products/<id>/options/<option_id>` |
| POST | `/api/products/<id>/options/<option_id>/values` |
| PUT · DELETE | `/api/products/<id>/options/<option_id>/values/<value_id>` |
| POST | `/api/products/<id>/variants` |
| PUT | `/api/products/<id>/variants/<variant_id>` |
| PATCH | `/api/products/<id>/variants/<variant_id>` — `{is_active}` |
| DELETE | `/api/products/<id>/variants/<variant_id>` |

**Why a service, not fat handlers.** CLAUDE.md: business logic lives in
`app/services/`, handlers stay under ~40 lines. The route file is ten
3-line handlers over a shared `_handle` wrapper; every rule (trilingual
validation, one-value-per-axis, combination uniqueness, the 409s) is in the
service and tested there.

**Rules worth recording:**

- A variant names **exactly one value on every axis**. "A vendor who sells
  red in small and black in medium creates those two rows, not four"
  (ADR 0035) is about not needing every *combination* — each variant still
  fully specifies the product's axes, because the customer picker resolves
  a variant by matching the complete set of option-value ids.
- The `product_variant_values` unique constraint stops a duplicate
  *value* on a variant, not a duplicate *combination* across variants —
  that check (`_combination_taken`) is in the service.
- **`delete_option` / `delete_value` refuse (409) while a variant still
  uses the value.** Cascading the delete through to live variants would
  silently drop what a customer's cart is pointing at.
- **`update_variant` sets stock with a plain `UPDATE`**, not the
  conditional `WHERE stock >= :qty` decrement `_reserve_variant_stock`
  uses. A vendor overwriting their own count is not racing a concurrent
  checkout the way two customers race each other (CL-06).

## Part B — retired variants are a non-owner filter, not a delete

`variant_fields` gained `include_inactive=False`. `get_product` passes
`include_inactive=_owns_store(product.store_id)`: the owning vendor sees
retired variants to manage them; the public product page lists only active
ones, so a customer can never pick a variant that no longer exists. This is
a **parameter on the existing function**, not a second serializer —
options and their values are returned in full either way, and a value that
no active variant uses simply fails to resolve in the picker, which shows
"that combination is not available".

## Why no hard-delete after an order

`DELETE /variants/<id>` works only for a variant that has **never** appeared
in an `order_items` row — a vendor undoing a mistake. Once an order
references it, `is_active: false` is the only retirement path:
`order_items.variant_id` must not dangle, and the denormalised
`order_items.variant_label_*` (ADR 0035) already means the customer's
history reads correctly without the variant row needing to carry live text.
Setting `is_active` false is the whole operation — a vendor may retire a
combination they still hold stock of.

## Part C / D / E — the UI

- **Vendor manager** — `frontend/src/pages/Vendor/VendorVariantManager.jsx`,
  rendered under `ProductImageManager` on the product edit page. Reuses
  `LanguageTabs` for every trilingual axis-name and value input (no second
  trilingual pattern). The pure resolution logic —
  `resolveVariant` / `selectionComplete` / `combinationTaken` — is in
  `frontend/src/utils/variants.js`, shared with the picker and unit-tested
  under `node --test`.
- **Customer picker** — `ProductDetails.jsx`: one row of buttons per axis;
  a full pick resolves to a variant whose `price` and `stock` then drive
  the price display, the availability line and the quantity cap (not the
  product's own, which for a variants-only product is a placeholder). Add
  to Cart is disabled until the combination resolves, mirroring the
  backend's `variant_required`.
- **Cart / order lines** — the variant label is rendered under the product
  name; the fields already arrived on the wire from V-1.

## Follow-ups still open

- **Per-variant images** — named in ADR 0035, still not this session.
- **Bulk combination generation** ("create all 6 of these 2×3 axes") — a
  vendor-UX nicety; the manager adds variants one at a time.
- **Editing or deleting an option value already used by an *order*** — the
  service blocks deleting a value used by a *variant*; a value referenced
  only through `order_items` history (its variant since deleted) is not a
  case that arises yet, but is the natural next edge.

## Verified

- `flask db check` clean; `flake8` clean; backend suite **540 → 548**
  (the ten new routes are covered by `test_product_variant_crud.py` and by
  the extended isolation test).
- `npm run lint` (17 warnings, 0 errors, unchanged), `lint:tokens` clean,
  `npm test` including `variants.test.js`, `npm run build` passes.
- Browser: the Hamra vendor edits "Lebanese Extra Virgin Olive Oil", sees
  the Size axis and its two variants, adds a "3L" value and a variant for
  it, then removes both; a shopper opens the product, picks 2L → price
  $12.00 → $22.00 and stock → "10 available", adds to cart, and the cart
  line reads "Lebanese Extra Virgin Olive Oil / 2L".
