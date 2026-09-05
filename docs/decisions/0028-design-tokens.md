# 0028 — Design tokens

**Date:** 2026-09-06
**Status:** accepted

## The problem

`frontend/src/index.css` was one line: `@import "tailwindcss";`. No
config file, no `@theme` block, no custom properties. Every colour in the
application was a literal utility written into a `className` — **1,948
of them across 83 files**, in 1,776 `className` attributes.

That is not merely untidy. It has three consequences:

- **No colour has a meaning.** `bg-white` on a card and `bg-white` on a
  translucent hero panel are the same string doing two unrelated jobs.
  Nothing records which is which, so nothing can change one without
  hunting for the other.
- **Nothing can be themed.** A dark mode, a high-contrast mode, or a
  white-label deployment would mean finding and arguing about 1,948 call
  sites one at a time.
- **The palette had already forked.** Twice by the count in the brief,
  and in fact four times.

## What the read pass found

Four split palettes, not two:

| role | ramps in use | uses |
|---|---|---|
| neutral | `gray` / `slate` | 854 / 242 |
| brand | `emerald` / `green` | 222 / 210 |
| warning | `amber` / `yellow` | 55 / 9 |
| info | `sky` / `blue` | 10 / 10 |

The emerald/green fork was the damaging one. Both were used for primary
buttons: the shared `Button` component's `primary` variant was
`bg-green-700`, while the navbar brand mark, the nav links and the cart
badge were `emerald-700`. Those are visibly different greens —
`oklch(52.7% 0.154 150.069)` against `oklch(50.8% 0.118 165.612)` — so
the application shipped two different brand colours depending on which
component you were looking at.

The second finding was that the design used more roles than a
first-pass token list would name. Bucketing all 1,948 uses against the
15 roles originally proposed:

```
map onto a named role       1348  (69%)
need a role not in the set   600  (31%)
```

and the gaps were systematic, not stray:

```
147  a fourth neutral text weight   gray-700 x100, gray-800 x22, slate-700 x21, slate-800 x4
112  the form focus ring            green-600 x86, emerald-600 x26
 71  a fifth neutral text weight    gray-400 x55, slate-400 x7, gray-300 x5, slate-300 x4
 61  a third neutral border weight  gray-100 x54, slate-100 x7
 60  the foreground on a fill       text-white x60
```

The frontend used **seven** neutral text weights and **three** neutral
border weights. Three text roles and two border roles cannot hold them
without changing pixels.

## The decisions

### Ramps: gray and emerald

**Neutral is `gray`** — 854 uses against 242, no contest.

**Brand is `emerald`** — 222 against 210, near enough even that the count
does not decide it. The tiebreak is that the navbar brand mark, the nav
links and the cart badge are emerald, so emerald is what a customer
already reads as "CedarLink". `Button`'s `primary` variant moved from
`green-700` to `brand`, which resolves to emerald-700.

**Warning is `amber`**, **info is `sky`**, on the same "which one is
already load-bearing" basis.

The choice matters less than there now being exactly one of each.

### Roles, not colours

Every token is `--color-<role>`: `--color-surface`, never
`--color-white`. A role survives a theme change and a colour does not.
`--color-surface` can become near-black in a dark theme and every call
site stays correct; `--color-white` would have to be renamed or would
start lying.

Several tokens deliberately share a value today — `--color-border` and
`--color-control` are both gray-200; `--color-border-strong`,
`--color-control-hover` and `--color-text-disabled` are all gray-300.
That is the point rather than a mistake: they are different roles that
happen to agree now and are free to diverge later without a search.

### 39 roles, and why that is a finding

The token set is larger than the 15 originally proposed, because the
brief also said the design must not change and the design genuinely used
those distinctions. Every addition is load-bearing at ≥5 call sites, and
each is named for what it does rather than what it looks like.

Thirty-nine is more roles than a healthy system needs. Seven neutral text
weights is a symptom of a design that grew without a vocabulary, not a
considered ramp. **Making that countable is the token layer's first
payoff** — before this change nobody could have said how many neutral
text weights the app used. Collapsing them is a design decision, and
this session was explicitly not allowed to make one.

### Values are literals, not `var()` indirection

`@theme` holds the literal oklch values rather than
`--color-surface: var(--color-gray-50)`. Tailwind 4 tree-shakes theme
variables no utility references, and after this migration nothing
references the raw ramp — the indirection would resolve to nothing. The
ramp and shade each value came from is in a trailing comment, so the
provenance stays readable.

## What changed on screen, and what did not

**84 files, 1,945 mechanical substitutions**, plus 10 targeted ones where
green meant "this went well" rather than "this is ours" (order-status
pills, the store open badge, the announcement live badge) and became
`success-*`.

The three remaining literals are `bg-transparent` and `border-transparent`
— Tailwind keywords meaning "no colour of my own", deliberately allowed.

**No JSX structure, route or component boundary changed.** Proven rather
than asserted: masking every colour utility (old form and new) out of
both revisions leaves all 83 changed source files byte-identical to
`HEAD`.

**Colour did change, by instruction**, on the losing half of each fork:
242 slate utilities, 210 green, 8 yellow, 10 blue — 470 of 1,948, about
24%. That is what resolving a split palette means; a token layer that
kept both ramps would have preserved every pixel and preserved the
problem. Verified live in the browser afterwards: the primary button now
paints `oklch(0.508 0.118 165.612)` (emerald-700, was green-700), the
navbar rule paints gray-200 (was slate-200), the brand mark is unchanged,
and every colour painted on the products page resolves to a token.

## The guard

`frontend/scripts/check-design-tokens.mjs`, wired in as
`npm run lint:tokens` and as its own CI step in the frontend job.

It fails on any `bg-white`, `text-gray-500`, `border-emerald-700`,
`hover:bg-green-800` or `bg-[#hex]` in `frontend/src`, with the file, the
line and the offending utility. `src/index.css` is the one exempt file,
because it is the file whose job is to map colours onto roles.

It is a text scan rather than an ESLint AST rule on purpose: Tailwind
classes are not syntax. They appear in string literals, template chunks,
ternary branches and plain lookup objects like `STATUS_TONE`. A regex
over the file finds all of those; an AST rule would have to re-find them
in each shape.

Without this the tokens erode. One `bg-white` merged on a Friday is not a
problem; twenty over a quarter are a second undocumented palette, and by
then nobody can tell which of the two is correct.

### Verified, not assumed

The same standard as the schema-drift guard (ADR 0016). Three raw
utilities of three different shapes were deliberately reintroduced into
`Cart.jsx` — a bare keyword, a variant-prefixed shade, and a plain shade
— and the check was run:

```
Design tokens: 3 raw colour utilities found.

  src/pages/Cart/Cart.jsx:68   bg-white              (bare white/black)
  src/pages/Cart/Cart.jsx:96   hover:bg-emerald-800  (palette shade)
  src/pages/Cart/Cart.jsx:202  text-gray-500         (palette shade)
```

exit code 1. The three were reverted and it returned to exit 0. A guard
never seen to fail is not a guard.

## Known cost

The text roles produce a stutter: `--color-text-muted` yields the utility
`text-text-muted`, and there are 181 of them. That is the literal
consequence of naming the roles `text-primary` / `text-secondary` /
`text-muted` while Tailwind prefixes the utility with the property. It
reads oddly and it is unambiguous — `bg-text-primary` is a legitimate
near-black background. Renaming the family to `ink-*` (`text-ink-muted`)
would read better and is a one-line change to `@theme` plus a rerun of
the same migration, if the stutter proves more annoying than the
consistency is worth.

## The alternative not taken

A `tailwind.config.js` with a custom palette (`colors: { surface: ... }`)
rather than a CSS `@theme` block. It works, and Tailwind 4 supports it
for compatibility — but v4's own direction is CSS-first configuration,
the values would not be real CSS custom properties, and a future dark
theme would have to be built out of `dark:` variants at every call site
instead of redefining the tokens once inside a media query or a
`[data-theme]` block.
