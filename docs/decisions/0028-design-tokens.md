# 0028 — Design tokens

**Date:** 2026-09-06
**Status:** accepted

## The problem

`frontend/src/index.css` was one line: `@import "tailwindcss";`. No
config file, no `@theme` block, no custom properties. Every colour in the
application was a literal utility written into a `className` — **1,948
of them across 83 files**, in 1,776 `className` attributes. (The figure
circulated beforehand was 1,933; 1,948 is the measured count and is the
one every number below is derived from.)

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


---

# Addendum, 2026-09-06 — CedarLink's own vocabulary

## The rename

The first pass named the families after what Tailwind calls them, which
produced two stutters that were noted as a known cost and then got worse
every time anyone read them: `text-text-muted` (181 occurrences) and
`border-border` (87).

More importantly, the redesign mockup is written in CedarLink's own
vocabulary, not Tailwind's. Renaming now makes the redesign a
**values-only change** — the mockup's role names and the codebase's role
names are the same words, so transcribing it means editing `@theme` and
nothing else. Renaming afterwards would mean touching every call site a
second time, during the one change where the diff most needs to be
readable.

| was | is | why |
|---|---|---|
| `text-*` | `ink-*` | kills `text-text-muted`; `text-ink-muted` reads |
| `surface*` | `paper*` | kills nothing, but pairs with ink |
| `border*` | `line*` | kills `border-border` |
| `brand*` | `cedar*` | the brand has a name, and it is not "brand" |

`on-brand` became `on-cedar` — the same rule, applied to the compound.
Status roles keep their names: "danger" and "warning" are already the
words a designer and a developer both use, and there was nothing to fix.

**1,686 renames across 81 files.** The masked-diff proof was rerun with
both vocabularies masked: 80 of the 81 files are byte-identical to the
previous revision. The one that is not is the role fix described below,
and its diff was read line by line.

## Two role errors, corrected

The first pass mapped literals onto roles by what they *looked like*.
Two places wanted a role by what they *meant*, and got the wrong one.

**A star is not a warning.** Star ratings were `warning-accent`, because
a filled star and a caution triangle are both amber-400. They are not the
same thing, and the binding is a trap: retuning the warning colour would
silently retune every star on the site, and nobody changing a warning
colour would think to check a rating. `--color-rating` now exists with
the same value and a different reason. Two of the four `warning-accent`
sites moved; the other two — the rejected-store alert triangle and a
caution border on the data-deletion screen — were genuinely warnings and
stayed.

**A white foreground on a red fill is not `on-brand`.** Checking the 60
`text-white → on-brand` substitutions found **five** sitting on a danger
fill (the `Button` danger variant, the navbar sign-out, a notifications
action, and two on the security screen), plus one on an amber fill in the
account-reactivation button. All were white, so all were invisible — and
all would be wrong the moment a theme wanted a different foreground on
red than on green. `--color-on-danger` and `--color-on-warning` now
exist. Three roles, three values, all `#fff` today, three separate
questions.

A seventh case was worse than the other six. `PrivacyData.jsx` set its
button's background from a prop:

```js
const btnClass = danger
  ? "bg-danger hover:bg-danger-strong"
  : "bg-cedar hover:bg-cedar-strong";
```

while the foreground sat fixed in the `className` as `text-on-brand`. The
fill switched and the foreground did not. The fix moves the foreground
into the same conditional, so the pair travels together. This is the one
file the masked-diff proof reports as changed, and deliberately so.

The token count went 39 → 42: `rating`, `on-danger`, `on-warning`. The
rename itself changed no values and no counts.

## The guard, widened before it is needed

The check now also fails on:

- `style="…"` attributes containing a colour literal,
- `style={{ … }}` objects containing one,
- any colour literal in a `.css` file other than `index.css`,
- and it scans `frontend/index.html` as well as `frontend/src`.

The reason is timing. The redesign will transcribe a mockup exported from
a design tool, and design tools export inline styles. A colour hidden in
`style={{ color: "#1f2937" }}` is exactly as untouchable by a theme
switch as `bg-white` — worse, because no linter reads it. Adding the rule
after the transcription would mean auditing the transcription; adding it
before means the transcription cannot introduce the problem in the first
place.

### Verified again, on the new shapes

Four raw colours of four shapes were reintroduced — a Tailwind keyword, a
`style={{}}` object, an arbitrary utility value, and a `style=""`
attribute in `index.html`:

```
Design tokens: 4 raw colours found.

  src/pages/Cart/Cart.jsx:68   bg-white                      (bare white/black)
  src/pages/Cart/Cart.jsx:69   style={{ color: "#1f2937" }}  (inline style object)
  src/pages/Cart/Cart.jsx:202  text-[rgb(120,120,120)]       (arbitrary utility value)
  index.html:28                style="background: hsl(0 0% 100%)"  (inline style attribute)
```

exit code 1, all four named with file and line. Reverted, back to exit 0.
