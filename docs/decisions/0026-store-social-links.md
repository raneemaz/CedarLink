# 0026 — Store social and contact links

**Date:** 2026-09-05
**Status:** accepted

## The problem

A store page carried a name, a description and a `contact_info` string.
Nothing let a vendor say "we are on Instagram" or "message us on
WhatsApp", which for a small Lebanese shop is often the primary way
customers reach them — the shopfront on CedarLink is not the only
shopfront they have.

Two things make this harder than a text field.

The first is what a vendor will type. Asked for an Instagram address, a
vendor will paste any of `hamragrocery`, `@hamragrocery`,
`instagram.com/hamragrocery`, or a full URL copied out of the app
complete with an `?igshid=` tracking parameter. All four mean the same
account. A field that accepts only one of them is a field most vendors
fill in wrong.

The second is what the value becomes. It ends up as the `href` of an
anchor on a public page. A vendor-supplied string in an `href` is a
stored cross-site scripting vector: `javascript:` and `data:` URLs
execute in the customer's session on CedarLink's origin, and the vendor
who typed it is the least trusted party in that transaction — anyone can
register as a vendor.

## The decision

A separate table, `store_social_links(id, store_id, platform, value,
created_at)`, unique on `(store_id, platform)`, with a `CHECK` on the
seven allowed platform names and an index on `store_id`.

### No `bio` or `website` column on `Store`

`Store.description` already exists and is the store's own words about
itself; a second free-text field means two fields with the same meaning,
and two fields with the same meaning are two fields that disagree. A
website is a link like any other, so it is a `website` row here rather
than a column — which also means it gets the same normalisation and the
same scheme check as everything else, instead of a second code path that
someone forgets to protect.

### The stored value is the finished href, built by us

`store_service.normalize_social_value` turns whatever was typed into one
canonical form per platform:

| Platform | Accepts | Stores |
|---|---|---|
| instagram / facebook / tiktok | handle, `@handle`, `host/handle`, full URL | `https://…/handle` |
| whatsapp | a number, with or without `+`, spaces or dashes | `https://wa.me/<digits>` |
| website | a bare domain or a full URL | the URL, scheme preserved |
| email | an address, with or without `mailto:` | `mailto:<address>` |
| phone | a number as above | `tel:+<digits>` |

So the value a customer's browser follows was assembled here out of the
vendor's input rather than being the vendor's input. A pasted URL for the
wrong platform is refused rather than rewritten: a Facebook URL in the
Instagram field is a mistake, and silently turning it into
`instagram.com/HamraGrocery` would invent an account.

An `http://` website is stored as `http://` and not upgraded — a small
Lebanese shop's site may genuinely have no certificate, and quietly
rewriting it produces a link that does not load.

### The scheme check is in the service, not the form

Only `http` and `https` may ever be submitted. `javascript:`, `data:`,
`file:` and everything else are a 400.

This is enforced in `store_service`, and it has to be: a check in the
vendor's React form is bypassed by sending `PUT
/api/stores/<id>/social-links` directly, which requires nothing more than
a vendor account and curl. The form's job is to explain the rule, not to
be the rule.

Control characters are rejected outright rather than filtered. Browsers
strip tabs, newlines and NULs from a URL before resolving its scheme, so
`java\tscript:alert(1)` navigates as `javascript:` while a naive prefix
check sees something harmless. Matching the browser's parser exactly is a
losing game; refusing the characters is not.

`mailto:` and `tel:` are never *accepted* — they are constructed, after
the address or number has been validated as an address or a number.

### The set is replaced by diffing, not by clearing

`PUT` sends the whole set. The service diffs it by platform: platforms
that are new are inserted, changed ones updated, missing ones deleted.

Clearing the collection and re-appending would be simpler and would be
broken. Within one flush SQLAlchemy emits INSERTs before DELETEs, so
re-sending a platform the store already has collides with the row that
has not been deleted yet — a UNIQUE violation on `(store_id, platform)`.
That is exactly how `set_interests` failed (ADR 0022), and the test
`test_replacing_an_overlapping_set_does_not_raise_an_integrity_error`
was confirmed to reproduce it against a clear-and-recreate
implementation before the diff was written.

Diffing also means a link the vendor did not touch keeps its row, so its
`created_at` stays honest.

## The preview endpoint

`POST /api/stores/<id>/social-links/preview` normalises a submission
without writing it, so the vendor form can show that `@hamragrocery`
becomes `https://www.instagram.com/hamragrocery` *before* the vendor
saves.

The alternative was reimplementing the rules in JavaScript. That is the
same mistake as a second column meaning the same thing: two
implementations that drift, one of which is the security boundary. One
extra endpoint is cheaper than a client-side copy of "what is safe to put
in an href".

## Outbound links

Every link on the customer-facing store page carries `target="_blank"`
and `rel="noopener noreferrer"`. Without `noopener` the opened page holds
a handle on CedarLink's tab through `window.opener` — and these
destinations were chosen by a vendor, not by us.

The icons carry no text, so each anchor has its own accessible name from
a per-platform string: "Hamra Grocery on Instagram", but "Call Hamra
Grocery" and "Hamra Grocery website". One "{{store}} on {{platform}}"
template reads correctly for Instagram and absurdly for Phone.

## The alternative not taken

A single free-text "links" blob on `Store`, one link per line. It needs
no migration and no table.

It also has no unique constraint, so nothing stops two Instagram lines;
no CHECK, so nothing constrains what a platform is; no per-platform
validation, so the scheme check has to re-parse the blob on every read;
and no way to render a specific icon without guessing from the string.
Every one of those is the schema doing work the application would
otherwise do badly.
