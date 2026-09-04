# 0024 — No card data

**Date:** 2026-09-05
**Status:** accepted

## The defect

`POST /api/payment-methods` accepted a **full card number** and stored
`sha256(pan)` in `PaymentMethod.number_hash`:

```python
def hash_card_number(card_number):
    return hashlib.sha256(card_number.encode("utf-8")).hexdigest()
```

CLAUDE.md has said, since the project's first week:

> Never store card numbers or anything derived from them, hashes
> included. Provider token + last four only.

The column violated that rule directly. The comment above it —
*"The raw card number is never stored"* — was true only in the narrowest
sense, and false in the sense that matters. It was also repeated as a
claim in the report, which is why it needed correcting rather than
quietly deleting.

## Why an unsalted PAN hash *is* the card number

Hashing protects a secret only when the secret is unguessable. A card
number is not:

- The first six to eight digits are the **BIN** — the issuer — which is
  public and usually already known from `brand` and `last4` sitting in
  the same row.
- The last digit is a **Luhn check digit**, fully determined by the rest.
- The remaining digits are the account number.

For a 16-digit PAN with a known BIN, that leaves on the order of **10⁸ to
10⁹ candidates**, every one of which can be generated and hashed offline.
SHA-256 is designed to be fast, which here works against us: a commodity
GPU does billions of SHA-256 operations per second, so the entire
candidate space falls in **seconds**. With `last4` in the same row the
space shrinks by another four orders of magnitude.

There was no salt, no pepper, no key derivation function and no work
factor. So the column was a reversible encoding of the card number, and
storing it was storing the number.

This is not a novel observation — it is why PCI DSS treats a hashed PAN
as still being cardholder data unless the hash is keyed, and why
"hashes included" is written into the rule rather than left implied.

## The fix: stop receiving the number

The change is deliberately not "hash it better". Any storable
transformation of a PAN keeps the endpoint inside PCI DSS scope, and the
strongest guarantee available to a system that does not need the number
is **never to receive it**.

`POST /api/payment-methods` and `PUT /api/payment-methods/{id}` now take:

| Field | Why |
|---|---|
| `brand` | So the customer sees "Visa" next to the card |
| `last4` | Read off the card by the customer — the four digits are not cardholder data on their own |
| `exp_month` / `exp_year` | So two saved cards are distinguishable and an expired one is visible |
| `label` | Cardholder name |

The client was changed to match: `AddPaymentMethod.jsx` and
`EditPaymentMethod.jsx` no longer have a card-number field, no longer
hold one in state, and no longer send one. The last-four input is
deliberately `autoComplete="off"` rather than `cc-number`, so the browser
does not offer to fill a whole card number into a four-digit box.

**A PAN-bearing field is refused, not ignored.** `reject_card_data`
returns 400 for any of `card_number`, `cardnumber`, `card_no`, `number`,
`full_number`, `pan`, `number_hash`, `cvv`, `cvc`, `csc`,
`security_code`. Silently dropping the field would let an older client
keep putting a card number on the wire believing it was being handled —
and the wire, the access log and the error tracker are exactly where it
must not appear. A loud 400 tells the caller to stop sending it.

CVV field names are refused for the same reason and a stronger one: a
security code may never be stored after authorisation under any
circumstances, so there is no configuration in which accepting one here
would be correct.

## What was dropped, and what was not lost

Migration `b42d5bab9108` drops `number_hash` and adds `exp_month` /
`exp_year`.

**Nothing read the column.** It was written in two places
(`create_payment_method`, `update_payment_method`) and never queried,
never serialised, never compared. In particular it was **not** used for
duplicate detection — the only two queries in the create path handle the
`is_default` flag and count existing cards. So dropping it removes no
capability, and there was nothing to replace with a
`(brand, last4, expiry)` key. CedarLink has never detected duplicate
saved cards; it still does not. If that is wanted later, that triple is
the right key, because it cannot reconstruct a number.

The drop is destructive on purpose. There is no backfill, and the
downgrade re-creates an empty column rather than restoring the digests —
restoring them would be restoring the defect. The data was seeded only.

## The related thing a reader should know

**Selecting a saved card charges nothing.** Checkout validates the chosen
card and creates the order, but it creates no `Payment` row and calls no
provider — `POST /api/payments` is a separate endpoint that checkout
never invokes, and there is no outbound provider call anywhere in the
codebase. The saved-card flow records an *intent*; the order is still
collected on delivery like every other order.

That matters here for two reasons. It explains why removing the PAN costs
nothing operationally: no code path ever needed the number, because no
code path ever charged anything. And it means `preferred_payment_method
= "card"` in `ShoppingPreferences` is reachable and does change what
checkout preselects, while still not moving any money — so the enum
should not be read as evidence that card payment is implemented.

## When card payment is actually built

The number must not reach this server then either. The pattern that keeps
it out of scope is client-side tokenisation: the browser posts the card
directly to the payment provider's own iframe or SDK, the provider
returns an opaque token, and CedarLink stores **that token** —
`provider`, `provider_customer_id` and `provider_payment_method_id`
already exist on the model for exactly this. The server sees a token it
cannot reverse, and the PAN never transits infrastructure we operate.

## Consequences

- `payment_methods.number_hash` is gone; `exp_month` / `exp_year` are new
  (migration `b42d5bab9108`, verified up-from-empty, down, up, with
  `flask db check` clean).
- The endpoint is out of PCI DSS scope for cardholder data, because it
  cannot receive any.
- 29 tests now cover this endpoint, which previously had **none** — a
  significant part of how a PAN-storing route survived review. They
  assert that every PAN- and CVV-shaped field is refused, that a refused
  request persists nothing, that no column in any table contains the
  digits after a rejected attempt, and that `number_hash` and friends are
  absent from the schema.
