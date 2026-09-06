/**
 * Theme resolution — the whole of the decision, in pure functions.
 *
 * Kept out of the React context on purpose: "does an explicit light
 * choice beat a dark device?" is a question with a right answer and no
 * DOM in it, so it is answerable by a unit test rather than by clicking
 * around. See utils/theme.test.js.
 */

export const THEMES = ["light", "dark", "system"];

export const DEFAULT_THEME = "system";

/**
 * Where the render cache lives, per identity.
 *
 * Namespaced by user id, because the pre-paint script cannot ask the API
 * who is signed in — it reads this and paints. On a shared browser a bare
 * key means the next person to load the page gets the previous person's
 * theme for a frame, which is a small leak of someone else's preference
 * and a visible flash. Signed-out visitors keep the bare key: there is no
 * id to namespace by, and nothing of anyone's to confuse it with.
 */
export const THEME_CACHE_KEY = "cedarlink_theme";

export function themeCacheKey(userId) {
  return userId == null ? THEME_CACHE_KEY : `${THEME_CACHE_KEY}:${userId}`;
}

/** Anything unrecognised — a stale cache, a hand-edited value — is system. */
export function normalizeTheme(value) {
  return THEMES.includes(value) ? value : DEFAULT_THEME;
}

/**
 * The attribute value for `<html data-theme>`, or `null` for "don't set
 * one".
 *
 * `system` deliberately resolves to `null` rather than to the current
 * device value: leaving the attribute off is what lets the
 * `prefers-color-scheme` block in index.css do the work, so the page
 * follows a device that changes while it is open, with no listener.
 */
export function themeAttribute(preference) {
  const theme = normalizeTheme(preference);
  return theme === "system" ? null : theme;
}

/**
 * What the viewer will actually see, given their preference and their
 * device. Used for the "System (dark)" label on the settings screen —
 * never for deciding what to render, which is CSS's job.
 */
export function effectiveTheme(preference, systemPrefersDark) {
  const theme = normalizeTheme(preference);
  if (theme !== "system") return theme;
  return systemPrefersDark ? "dark" : "light";
}

/** Put the choice on the document root. Safe to call before React mounts. */
export function applyTheme(preference, root) {
  const element =
    root || (typeof document === "undefined" ? null : document.documentElement);
  if (!element) return null;

  const attribute = themeAttribute(preference);

  if (attribute === null) {
    element.removeAttribute("data-theme");
  } else {
    element.setAttribute("data-theme", attribute);
  }

  return attribute;
}

export function readThemeCache(userId, storage) {
  const store =
    storage || (typeof localStorage === "undefined" ? null : localStorage);
  if (!store) return DEFAULT_THEME;

  try {
    return normalizeTheme(store.getItem(themeCacheKey(userId)));
  } catch {
    return DEFAULT_THEME;
  }
}

export function writeThemeCache(preference, userId, storage) {
  const store =
    storage || (typeof localStorage === "undefined" ? null : localStorage);
  if (!store) return;

  try {
    store.setItem(themeCacheKey(userId), normalizeTheme(preference));
  } catch {
    /* storage unavailable — the choice still applies for this session */
  }
}
