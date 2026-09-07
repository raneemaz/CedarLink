# 0034 — Scroll reset on navigate

**Date:** 2026-09-07
**Status:** accepted

## The bug

There was no scroll handling anywhere in `frontend/src`. React Router
keeps the window scroll offset across a route change, so navigating from a
scrolled page to a shorter one left the new page scrolled past its own
content — it rendered as a blank strip until the user scrolled up.
Reported on Settings → Shopping Preferences; it was app-wide.

## The fix

`frontend/src/components/common/ScrollToTop.jsx` — renders nothing,
mounted once in `main.jsx` inside `<BrowserRouter>`, above `<App />`.

- **`useEffect` keyed on `[pathname, hash]`**, not the whole location. A
  query-string-only change — a filter, a page-number bump that stays on
  the same route — must not yank the page to the top. Verified live:
  Products "Next" (→ `/products?page=2`) keeps the scroll offset;
  Settings → a nested settings page resets it.
- **Skipped when `location.hash` is non-empty** — an in-page anchor link
  should scroll to its anchor, not to the top.
- On a POP (browser back/forward) `pathname` also changes, so back also
  lands at the top rather than at the forward page's offset. The spec
  accepts this ("plain `scrollTo(0, 0)` on every pathname change").

## The one thing beyond the spec: `history.scrollRestoration = "manual"`

The spec asked for `window.scrollTo(0, 0)` and nothing else. Manual
verification of the back button showed that alone is **janky**: the
browser's native scroll restoration (`scrollRestoration: "auto"`) runs
*asynchronously* as the destination page re-fetches and grows, and it
raced our reset — "back" from a tall Products listing landed on a stale
middle offset (~1462px), not the top and not the real previous position.

Setting `history.scrollRestoration = "manual"` in a mount-once effect
(restored on unmount) removes the race: this component becomes the only
thing that moves the scroll, and every navigation — PUSH or POP — ends at
the top, deterministically. Re-verified: back now goes straight to 0 and
stays there while content loads.

This does not change the *behaviour* the spec chose (back goes to top, not
to the old offset) — it just makes that behaviour clean instead of
flickering. A true "restore the exact previous offset on back" would need
per-history-key offset storage; the spec explicitly did not ask for that.

## Verified

- Settings (scrolled 4161px) → Shopping Preferences → **0**; back → **0**.
- Products (scrolled 6882px) → a product detail → **0**; back → **0**,
  stable as the listing re-renders.
- Products (scrolled) → "Next" (`?page=2`) → **offset kept** (no reset on
  a query-only change).
- `npm run lint` 0 errors / 17 warnings (unchanged), `lint:tokens` clean,
  `npm test` 19/19, `npm run build` passes.
