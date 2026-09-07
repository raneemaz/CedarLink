import { useEffect } from "react";
import { useLocation } from "react-router-dom";

/**
 * Reset the window scroll to the top on every route change.
 *
 * React Router keeps the previous page's scroll offset across a navigation,
 * so without this a new page can render as a blank strip until the user
 * scrolls up (seen on Settings → Shopping Preferences, but it is app-wide).
 *
 * Keyed on `pathname` and `hash`, deliberately not the whole location: a
 * query-string-only change (a filter, a page-number bump that stays on the
 * same route) must not yank the page back to the top. And when the URL
 * carries a hash the browser is scrolling to that anchor — leave it alone.
 *
 * Mounted once, above <App />, inside <BrowserRouter>. Renders nothing.
 *
 * Back/forward: `pathname` changes on a POP too, so those also land at the
 * top rather than wherever the page you came from was scrolled. The
 * spec accepts this ("plain scrollTo(0,0) on every pathname change"); the
 * browser's own scroll restoration is switched to `manual` so it does not
 * race our reset as the new page's content loads (that race left "back"
 * on a stale middle offset — verified before the fix).
 */
export default function ScrollToTop() {
  const { pathname, hash } = useLocation();

  // Turn off the browser's own scroll restoration on back/forward. It runs
  // asynchronously as the new page's content loads and grows, which races
  // the effect below — without this, hitting "back" from a tall page lands
  // on a stale middle offset (verified: ~1462px on Products) instead of
  // cleanly at the top. With `manual`, this component is the only thing
  // moving the scroll, and every navigation — PUSH or POP — ends at the
  // top, deterministically.
  useEffect(() => {
    const previous = window.history.scrollRestoration;
    if (previous) {
      window.history.scrollRestoration = "manual";
    }
    return () => {
      if (previous) {
        window.history.scrollRestoration = previous;
      }
    };
  }, []);

  useEffect(() => {
    if (hash) return;
    window.scrollTo(0, 0);
  }, [pathname, hash]);

  return null;
}
