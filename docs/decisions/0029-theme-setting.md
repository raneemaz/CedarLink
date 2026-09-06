# 0029 — Theme setting (light / dark / system)

**Date:** 2026-09-06
**Status:** accepted

## What this cost

**No component changed.** Not one `className`, not one JSX node, not one
route. The entire feature is a second set of values for the roles defined
in ADR 0028, plus a preference column, a settings screen and eleven lines
of inline script.

That is the return on the token layer, and it is the only reason a dark
theme was a session's work rather than a month's. Before ADR 0028 this
would have meant finding 1,948 literal colour utilities and deciding, one
at a time, what each of them should become in the dark.

## Where the values live

`index.css`, in two blocks after `@theme`:

- `:root[data-theme="dark"]` — an explicit dark choice.
- `@media (prefers-color-scheme: dark) { :root:not([data-theme="light"]) }`
  — the device preference, for anyone who has not chosen.

The `:not([data-theme="light"])` guard is the whole of the precedence
rule: on a device set to dark, a user who has explicitly chosen light
still gets light. Specificity decides, not source order — `@theme` emits
into `:root` (0,1,0), `:root[data-theme="dark"]` is (0,1,1) and
`:root:not([data-theme="light"])` is (0,2,0) — so neither block depends
on where Tailwind chooses to hoist its output.

`color-scheme` is set alongside, so the browser's own chrome (form
controls, scrollbars, the canvas behind the page) matches. Without it a
dark page keeps white scrollbars.

### Three deliberate inversions

Most roles simply walk to the other end of their ramp. Three do not:

- **`paper-sunken` becomes lighter than `paper-raised`**, where in light
  it is darker. An inset reads as an inset by *differing* from the card;
  going darker in a dark theme merges it into the page instead.
- **Brand and status colours move to the light end.** `emerald-700` on a
  near-black card is 1.9:1 — legible as a shape, not as text. Cedar
  becomes `emerald-400`, danger `red-400`, warning `amber-300`, info
  `sky-300`.
- **`on-cedar` / `on-danger` / `on-warning` become near-black**, because
  the fills they sit on are now light. This is precisely the case that
  justified splitting them out of one shared `on-brand` in the ADR 0028
  addendum; had they stayed a single token, dark mode would have painted
  black text on a green button and white text on nothing.

`rating` is unchanged. A gold star is gold on any ground.

## Where the preference lives

`users.theme`, an enum of `light` / `dark` / `system`, `NOT NULL`,
`server_default 'system'` — the same shape as `language` and `currency`
beside it, and for the same reason: the choice follows the person between
their phone and their laptop rather than living in one browser.
`PUT /api/users/<id>/theme`, owner-only, value checked against a
server-side list.

`system` is the default because it is the only value that is right before
anyone has been asked.

A signed-out visitor gets `system` too, and their choice is remembered in
`localStorage` only — there is no account to attach it to, and inventing
one for a colour preference would be worse than forgetting it.

## No flash on load

The bundle cannot be the thing that decides the theme, because by the
time it runs the browser has already painted. So `index.html` stamps
`data-theme` in `<head>`, in the same inline script that already orients
`dir` for Arabic:

```js
var theme = localStorage.getItem("cedarlink_theme");
if (theme === "light" || theme === "dark") {
  document.documentElement.setAttribute("data-theme", theme);
} else {
  document.documentElement.removeAttribute("data-theme");
}
```

`system` deliberately sets **no** attribute rather than resolving to the
current device value. Leaving it off is what lets the
`prefers-color-scheme` block keep deciding, so a device that switches
while the page is open is followed with no listener and no re-render.

That script is a hand-written copy of `themeAttribute()` from
`utils/theme.js`, which is a duplication with a reason (it must run
before any module loads) and therefore a risk. A test asserts the two
agree by reading `index.html` itself.

## Testing

The interesting logic was pulled out of the React context into
`utils/theme.js` as pure functions, so the questions with right answers
can be asked without a DOM: **10 tests** under Node's own runner
(`node --test`, no framework added), covering the default, an unknown
value, `system` setting no attribute, an explicit light choice beating a
dark device and vice versa, cache round-trip, a corrupt cache, storage
that throws, and the `index.html` agreement above.

**14 backend tests** cover the API half: the default on a new account,
round-trip for all three values, appearance in the profile payload,
rejection of six unsupported values (including `"Dark"` and `"light "` —
case and whitespace are not silently forgiven), one user unable to set
another's, and a signed-out request refused.

"No component renders differently between themes except in colour" is
enforced rather than tested. The design-token check now also fails on any
`dark:` variant in `frontend/src`: with no colour literals and no `dark:`
variants anywhere, the only thing that *can* differ between the two
themes is a token value. Verified the same way as the rest of that guard,
by adding `dark:bg-gray-900` to a className and watching it exit 1.

## Contrast

Computed from the shipping values by `frontend/scripts/check-contrast.py`
— it parses `index.css`, converts oklch to sRGB and applies the WCAG 2.1
relative-luminance formula, so the figures cannot drift from what is
deployed. Reproduce with `python frontend/scripts/check-contrast.py dark`.

Text on `paper-raised` (the card surface, where most text sits):

| role | ratio | AA |
|---|---|---|
| `ink` | 17.00 | pass |
| `ink-emphasis` | 16.13 | pass |
| `ink-body` | 14.35 | pass |
| `ink-secondary` | 12.06 | pass |
| `ink-muted` | 6.82 | pass |
| `ink-faint` | 3.67 | large text only |
| `ink-disabled` | 2.35 | below both |
| `cedar` | 9.18 | pass |
| `danger` | 6.14 | pass |
| `warning` | 12.27 | pass |
| `info` | 10.65 | pass |

Across all three surfaces (`paper`, `paper-raised`, `paper-sunken`) the
worst body-text ratio in the dark set is **5.08:1** (`danger` on
`paper-sunken`) and the worst filled-block pair is **5.01:1** (`cedar` on
`cedar-tint`). Every body role clears 4.5:1 on every surface.

Two honest exceptions, neither of them body text:

- **`ink-faint`** ranges 3.04–4.16 across the three surfaces. It clears
  the 3:1 large-text bar everywhere and is used for icons and secondary
  metadata, not for reading. It is *better* than the same role in the
  light theme, which is 2.36–2.60 and clears neither bar.
- **`ink-disabled`** is 1.94–2.66. WCAG 2.1 SC 1.4.3 explicitly exempts
  text in inactive user-interface components, which is the only place
  this role is used. The light theme's equivalent is 1.34–1.47, so again
  the dark set is the better of the two.

Stated plainly because chapter 7 will want to claim the theme is
accessible: **every body-text role passes AA in dark, on every surface,
with margin.** The two roles that do not are a decorative one that meets
the large-text bar and a disabled one the specification exempts — and
both are worse in the light theme that has been shipping all along. If
anything, this session improved the accessibility of the light theme's
weakest pairs by giving the project a script that measures them.

## The alternative not taken

`dark:` variants at each call site, which is Tailwind's own default
answer. It needs no token layer and no CSS block — and it would have
meant editing every one of the 1,948 colour call sites, would have put
the palette back inside the components where it cannot be reviewed as a
whole, and would have made a third theme (high contrast, say) another
full pass. The check now refuses them for that reason.
