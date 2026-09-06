# 0030 — Visual design

**Date:** 2026-09-06
**Status:** accepted

## What this session was

CedarLink's frontend was **correct and undesigned**. Every page worked,
every string was translated, every layout mirrored under RTL — and there
was no token layer, no type scale, two neutral ramps and two greens
quietly disagreeing across 1,948 hard-coded colour utilities. That was
not visible by reading the code; it became visible by counting it (ADR
0028).

This session gave it a design. Because ADRs 0028–0029 had already put a
role vocabulary in place, the palette change was **the `@theme` block and
nothing else** — no component read a colour, so no component had to
change to get a new one.

The source is the redesign mockup: four artboards on a design canvas,
with the component sheet authoritative wherever an artboard disagreed
with it.

## Step 1 — the Arabic typefaces, and why this came first

The mockup specifies Newsreader and Plus Jakarta Sans. **Neither ships a
single Arabic glyph.** Verified rather than recalled, by fetching the
Google Fonts `css2` response with a desktop user-agent and reading the
`unicode-range` declarations:

| family | subsets served |
|---|---|
| Newsreader | latin, latin-ext, vietnamese |
| Plus Jakarta Sans | cyrillic-ext, latin, latin-ext, vietnamese |

Newsreader's widest range ends at `U+A720-A7FF`. Neither family touches
`U+06xx`, `U+FB50-FDFF` or `U+FE70-FEFF`.

A trap worth recording, because it is how a from-memory check gets this
wrong: a naive grep for `U+FE` "finds" Arabic in both faces. It is
matching `U+FEFF`, the byte-order mark.

Had the mockup shipped as drawn, **every Arabic screen would have fallen
back to whatever the OS picked** — no design at all in the language a
third of the report's figures are in, and nothing in the build, the tests
or the browser would have said a word.

### The pairing

| role | face | why |
|---|---|---|
| Display · AR | **Amiri** 400/700 | A revival of the Bulaq press types — classical Naskh with a printed-book warmth that mirrors Newsreader in structure and in temperament |
| Interface · AR | **IBM Plex Sans Arabic** 400–700 | Drawn alongside a Latin sibling, so prices, Latin brand names and percentages sit level inside Arabic sentences |
| Fallback | Noto Naskh Arabic → Tajawal → system | A real stack, so a blocked font host degrades to a designed face |

Rejected and worth recording: **Reem Kufi + Readex Pro** is coherent, but
a serif heading in English beside a geometric Kufic heading in Arabic is
two brands in one palette. **Cairo** is competent and everywhere, which
is the problem — it is what an Arabic site looks like when nobody chose.
**Aref Ruqaa** is a wordmark face working too hard at 26px.

### Three corrections to the mockup's CSS

All three were in the mockup as written, and all three would have shipped
as defects nobody reports, because the people who notice are the ones
reading in Arabic. Verified live in the browser under `dir="rtl"`:

| correction | measured |
|---|---|
| `letter-spacing: normal` — tracking severs the joins in a joined script | body and `h1` both report `normal` |
| `line-height: 1.95` body / `1.5` headings — the mockup's `1.06` clips the vowel marks | body `33.07px` (16.96 × 1.95), `h1` `69.96px` |
| `font-size: 106%` — no capitals, so the same pixel size reads lighter | root `16.96px` |

Amiri has no 500 or 600, so Newsreader 600 maps to **Amiri 700** rather
than letting the browser synthesise a bold, which smears the strokes.
Confirmed: `h1` computes `font-weight: 700`, `font-family: Amiri`.

### Self-hosted

All four families are served from `/fonts`, not linked. A design that
depends on a reachable CDN degrades to nothing, and
`fonts.googleapis.com` is blocked in enough places that "it works here"
is not evidence.

Only the subsets CedarLink renders are stored — `latin` for the Latin
families, `arabic` for the Arabic ones — and `unicode-range` is kept
verbatim from Google's own CSS, so a browser downloads an Arabic face
only for a page that has Arabic on it. Confirmed in the browser: on the
English home page all four Arabic faces report `unloaded`; on the Arabic
page Amiri 700 and all four Plex Arabic weights load and the Latin
families do not.

**546 KB across 8 files.** Newsreader and Plus Jakarta Sans are variable
fonts — Google serves the same bytes for every weight — so storing one
file per weight was 214 KB of duplicate font. One file each, with a
`font-weight` range.

## Step 2 — the palette

The mockup's names map onto the existing roles; **no role was renamed, so
no call site changed**:

```
--paper      -> paper          --cedar-900 -> cedar-strong
--paper-2    -> paper-sunken   --cedar-700 -> cedar
--ink        -> ink            --cedar-500 -> cedar-ring
--ink-muted  -> ink-muted      --cedar-100 -> cedar-tint
--line       -> line           --cedar-50  -> cedar-subtle
--copper-600 -> copper         --copper-700 -> copper-strong
```

**One role was added.** The mockup uses copper for sale prices and the
quick-add affordance, and the previous set had no accent role. Writing
the literal at each site is exactly what the lint guard exists to stop,
so the role was added — `copper-tint` / `copper` / `copper-strong`, plus
`on-copper` for a label on a copper fill.

**A second was added for accessibility**, not for the mockup:
`rating-empty`, below.

The mockup gives one neutral text weight and one border weight; the
application uses seven and three. The extra steps are interpolated along
the same hue (80/85) rather than invented, so the ramp reads as one
family, and every one is measured.

Dark values are re-derived against the new palette rather than carried
over: the ground is a warm near-black at hue 80, not a blue-grey, so the
two themes read as one palette.

## Step 3 — the type scale

Newsreader for `h1`/`h2` and display numerals, Plus Jakarta Sans for
everything else. Sizes from the component sheet, as tokens — a
hard-coded `text-[27px]` is the same mistake as a hard-coded colour:

| token | size | use |
|---|---|---|
| `text-display` | 44px | hero |
| `text-title` | 27px | section headings |
| `text-body` | 16px | body |
| `text-small` | 14px | secondary |
| `text-micro` | 12px | badges, metadata |

Radii and shadows likewise: `rounded-card` (20px), `rounded-control`
(12px), `rounded-pill` (999px), and green-tinted shadows
(`0 16px 32px -16px`) rather than grey ones — a neutral drop shadow on a
warm paper ground reads as dirt.

## Step 4 — the components

**1,135 substitutions across 81 files**, applied mechanically: shape and
type utilities mapped onto the new tokens, the same technique as the R1
colour migration. Colour does not appear in that diff at all, because
colour was already a token.

The state work the sheet specifies by hand:

- **Buttons** — pill radius, the sheet's 13/24 padding, four variants
  plus a real disabled treatment. Disabled is a variant rather than an
  opacity wash: a 50%-opacity cedar fill on warm paper turns muddy green.
- **Badges** — "Closed" became a neutral warm chip rather than a red one.
  A shut shop is not an error.
- **Product card** — 4px lift on hover with the quick-add revealed,
  180ms, all in logical properties so it mirrors.
- **Rating** — see below.

## The hero stat

The mockup reads "120+ local stores, live count". It was never in the
code, so nothing had to be removed — but the stat is worth having and it
had to be real. It is bound to `total` from `GET /api/stores`, renders
only once it has a number, and currently shows **6**, which is how many
visible stores the seed produces. A fabricated figure on the home page is
the first image in the report.

## The unselected star — the one place the mockup gives way

`StarRatingInput`'s unselected star is the affordance that tells a
customer the control is clickable. That makes it the visible state of an
**active** user-interface component, which puts it under **SC 1.4.11 at
3:1** — not under the SC 1.4.3 inactive-control exemption, which is what
ADR 0029's audit established.

It measured **1.47:1**. The mockup draws it as a faint outline, lighter
still. It now has its own role, `rating-empty`, darkened until it clears
the floor, and **the pair is in the contrast gate** so it cannot drift
back:

```
light  rating-empty on paper-raised  3.37:1  (floor 3.0)
light  rating-empty on paper         3.18:1
dark   rating-empty on paper-raised  3.65:1
dark   rating-empty on paper         3.99:1
```

## Contrast

Computed from the shipping values by `frontend/scripts/check-contrast.py`,
which runs in CI and fails the build. **`KNOWN_FAILURES` is empty** — the
seven light-theme failures inherited from the pre-token colours are all
cleared by this palette, and the gate reports a stale entry as an error,
so the list cannot outlive the problem.

Light theme, on the card surface:

| role | ratio | | role | ratio |
|---|---|---|---|---|
| `ink` | 16.91 | | `cedar` | 9.61 |
| `ink-emphasis` | 13.65 | | `danger` | 7.11 |
| `ink-body` | 10.45 | | `warning` | 8.33 |
| `ink-secondary` | 8.12 | | `info` | 7.99 |
| `ink-muted` | **6.55** | | `warning-muted` | 6.18 |
| `ink-faint` | 3.95 (large) | | `cedar-strong` | 16.19 |

The two pairs flagged as tight before the work:

| pair | before | after |
|---|---|---|
| `ink-muted` on `paper` | 4.63 | **6.18** |
| copper on white | — | **4.94** |

`copper` on white is **4.94:1** and `cedar-ring` on `paper` is **4.72:1** —
both pass, both with about a quarter-point of headroom, and both are the
values to check first after any future tweak. Their derived states were
measured rather than assumed: `on-copper` on a copper fill is 4.94:1
light and 9.37:1 dark; `copper-strong` on white is 7.21:1.

One value moved for contrast rather than for design: `on-warning` became
white and `warning-muted` was darkened to `oklch(50% 0.1 60)`. Ink on a
mid-amber fill tops out at 2.98:1 wherever the amber sits, because both
are dark — the fix is the foreground, not the fill.

## RTL

Logical properties only. `grep` for `left-N`, `right-N`, `pl-`, `pr-`,
`ml-`, `mr-` across `frontend/src` returns **zero**. The card lift, the
quick-add reveal and the hero decoration all mirror because none of them
names a side.

Verified in the browser on the vendor dashboard chart:

| | axis border | day 1 | day 30 |
|---|---|---|---|
| English | left | x=54 | x=215 |
| Arabic | right | x=204 | x=48 |

**A correction to the brief.** It asked me to update a
`test_…rtl…` asserting x=54 and x=219. **No such test exists** — `grep`
across `tests/` and `frontend/src` finds no RTL or axis assertion, and
pytest collects none. Those coordinates were browser measurements
reported in the R1 session write-up, not committed evidence. The
mirroring is re-verified above and the numbers have moved (day 30 in
English 228 → 215; the Arabic figures moved further because the 106%
Arabic font-size widens the labels), but chapter 6 should not cite this
as a test until one exists. Writing one needs a browser-driving harness
— jsdom does no layout — which is a new dependency and a separate
decision.

## Deferred — chapter 9.3 future work, not omissions

Three items in the mockup are features wearing a redesign's clothing.
Each was examined and each is larger than it looks:

- **The cart drawer.** `/cart` is a page with tests and a report figure
  that assume a page. The `CartDrawer` artboard is a slide-over: a new
  component, a new interaction, and a different navigation model.
- **The mobile bottom tab bar.** A second navigation system, not a
  breakpoint. The report makes no mobile claim, the screenshot checklist
  has no mobile figures, and every figure is specified at 1440×900 —
  building it properly and then not photographing it earns nothing.
- **Dual USD + LBP pricing.** CedarLink shows one currency at a time via
  `CurrencyContext` and `currency_preference`. Showing both means
  `Price.jsx` renders two numbers, which needs a rate at render time for
  every price on the page and reopens the rate-pinning question parked as
  D-6.

## What did not move

No route, no page, no component boundary. `App.jsx` is untouched; no file
under `pages/` or `components/` was added or removed; the only export
that appears in the diff is `Button`'s, unchanged. The raw-colour lint
guard passes, which is the machine-checked half of the same claim: not
one literal colour, inline style or `dark:` variant was written.
