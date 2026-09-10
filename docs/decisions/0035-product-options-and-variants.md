# 0035 — Product options and variants

**Date:** 2026-09-10
**Status:** accepted
**Queue item:** V-1 (backend only; the vendor and customer UI is V-2)

## The gap

CedarLink stored exactly one `price` and one `stock` per product. A wool
scarf that comes in three colours, a bottle of olive oil in 1L and 2L at
different prices — there was no way for a vendor to sell "the same product,
several ways," and no way for a customer to say which one they wanted. It
is not only a labelling problem: the 2L bottle is not priced like the 1L,
so it touches price and stock both.

This ADR covers the schema, the migration, and the pricing / stock-decrement
changes. No UI was built in this session — that is V-2, sequenced after
this so the parts that touch checkout pricing and the CL-06 oversell
guarantee are reviewed before anything is built on them.

## Schema — four tables, all additive

- **`product_options`** — one row per option axis on a product ("Colour",
  "Size"). Trilingual `name_en/ar/fr` like every other name in the schema
  (ADR 0012).
- **`product_option_values`** — one row per value within an axis ("Red",
  "1L"). Trilingual `value_en/ar/fr`.
- **`product_variants`** — one row per combination a vendor actually
  stocks. `price` (nullable `Numeric(10,2)`), `stock` (`NOT NULL`, with the
  same `stock >= 0` CHECK `products.stock` carries), `is_active`, `sku`.
- **`product_variant_values`** — the (variant, option value) join.
  Surrogate `id` plus `UNIQUE(variant_id, option_value_id)`, keyed the way
  `store_social_links` keys a per-store-per-platform row rather than with a
  composite primary key.

Plus two nullable, additive columns each on `cart_items` and `order_items`
(`variant_id`; and on `order_items`, `variant_label_en/ar/fr`).

### Why variants are optional per product, not a required migration

A product with zero rows in `product_options` is unaffected in every way:
its own `price` and `stock` stay authoritative, and it serializes on the
wire byte-for-byte as before — `options` / `variants` keys appear only when
they exist. This is deliberate:

- The other ~60 seeded products (and the reviews, orders, coupons and
  dashboard lists built on them) need no data migration and no reshaping.
- The feature is provable on a handful of products without touching the
  rest — the seed adds options to exactly two.
- The migration is four `CREATE TABLE`s and six nullable columns. Nothing
  existing is renamed or dropped; every new foreign key is nullable.

### Why price *and* stock live on the variant, not just stock

The 1L/2L olive-oil case is a *pricing* difference, not only a stock one.
If only stock lived on the variant, a vendor could not charge more for the
2L. `product_variants.price` is nullable: set, it is the price for that
variant and the product's own price is ignored for it; null, the variant
falls back to the product's price (the scarf case — same price across
colours, so all three variant rows leave `price` null).

Once a product has variants, `products.stock` stops being read for
purchasing that product — the variant's stock is authoritative. The column
is not deleted; it is just no longer consulted while variants exist.

### The denormalised `variant_label_*` on `order_items`

An order placed against "Red, Medium" must still read "Red, Medium" on the
customer's history even if the vendor later renames the value or retires
the variant. So the label — each option value in its own trilingual text,
joined in display order, e.g. "Red, Medium" — is built at checkout time and
stored on the order item in three languages.

**A correction to the V-1 prompt.** The prompt said this mirrors an
existing `order_items.product_name_en/ar/fr` denormalisation. That
denormalisation does **not** exist today: `OrderItem` carries only
`product_id`, `quantity`, `unit_price`, and the order serializer reads
`item.product.name_en` live. So `variant_label_*` *introduces* the pattern
here rather than following it. The product name being a live read on order
history is a pre-existing latent gap (a soft-deleted product's row still
holds its name, so it has not bitten yet) — noted here, not fixed in this
session.

## What changed in the code

- **Pricing.** `order_service.resolve_unit_price(product, variant)` is the
  one place a line's unit price is decided. Every caller goes through it —
  `price_cart` (which both `/orders/preview` and `/orders` call, CL-15),
  the cart summary (`_cart_goods_by_store`), and the checkout write. It was
  one function but three call sites; all three now resolve the same way, so
  a quote and a charge still cannot diverge.
- **Stock decrement.** `order_service._reserve_variant_stock` is a
  *deliberately separate* conditional `UPDATE` against
  `product_variants.stock` — `WHERE id = :id AND stock >= :qty`, rowcount 0
  is the out-of-stock error. The CL-06 statement (`_reserve_stock`) is
  untouched and still handles plain lines. Two similar statements, each
  with its own barrier test, was judged safer this close to freeze than
  one merged clever one. `cancel_order` restores to whichever it took
  from.
- **Cart.** `add`/`update` validate the variant belongs to the product and
  is active, and check its stock. A product with active option axes refuses
  a plain add (`code: "variant_required"`) — with no single price or stock,
  the customer has to choose.
- **Serializers.** The product *detail* endpoint gains `options` /
  `variants` when they exist; the grid card is unchanged. Cart and order
  item payloads gain the resolved label and price on a variant line only.

## Follow-ups (named, not built)

- **Per-variant images.** A red scarf and a black one look different; this
  session did not add variant-specific images. A real feature on its own.
- **Editing or deleting an option value already used by an order.** Out of
  scope now. `is_active` lets a vendor retire a variant without deleting
  its history; a fuller edit/delete story (and what it does to open carts)
  is future work.
- **`order_items.product_name_*` denormalisation** — the latent gap above.

## Verified

- `flask db upgrade` / `downgrade` round-trips; `flask db check` clean
  (the CI drift gate, ADR 0016).
- `flake8 app tests run.py` clean.
- Full suite **529 → 540**, all green. New tests: unit price resolution
  (`test_variant_pricing.py`), variant checkout end to end including the
  trilingual label and a mixed plain+variant cart
  (`test_variant_checkout.py`), and a new barrier test proving the
  variant-level decrement cannot oversell — a new proof for new code, not
  a re-run of CL-06 (`test_concurrent_variant_checkout.py`).
- `flask seed` and `flask seed --reset` run clean. Seeded: the Wool Winter
  Scarf gets a Colour axis (Black/Grey/Burgundy, price null → falls back,
  stock 9/6/3); a new "Lebanese Extra Virgin Olive Oil" product on Hamra
  Grocery gets a Size axis (1L @ 12.00, 2L @ 22.00) with two reviews. The
  reviewed 1L product is untouched.
