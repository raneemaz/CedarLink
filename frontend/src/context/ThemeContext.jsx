import {
  createContext,
  useCallback,
  useContext,
  useEffect,
  useMemo,
  useState,
} from "react";

import api from "../services/api";
import { useAuth } from "./AuthContext";
import {
  DEFAULT_THEME,
  applyTheme,
  effectiveTheme,
  normalizeTheme,
  readThemeCache,
  writeThemeCache,
} from "../utils/theme";

const ThemeContext = createContext(null);

function systemPrefersDark() {
  if (typeof window === "undefined" || !window.matchMedia) return false;
  return window.matchMedia("(prefers-color-scheme: dark)").matches;
}

/**
 * The account is the source of truth for a signed-in user's theme, the
 * same arrangement `language` and `currency` already have: the choice
 * follows the person between their phone and their laptop rather than
 * living in one browser.
 *
 * localStorage is a render cache for them and the only store for a
 * signed-out visitor. It is namespaced by user id so one account's choice
 * can never be painted for another, and the signed-out entry has no id.
 *
 * This provider renders no markup and reads no colour. All it does is put
 * an attribute on `<html>`; index.css does the rest.
 */
export function ThemeProvider({ children }) {
  const { user } = useAuth() || {};
  const userId = user?.id ?? null;

  // Read per identity, then kept current by setTheme. This is the whole
  // store for a signed-out visitor and a render cache for everyone else.
  const [cached, setCached] = useState(() => readThemeCache(null));

  // The choice this session made, tagged with who made it so it is
  // discarded rather than inherited when the account changes.
  const [chosen, setChosen] = useState(null);

  const [isDarkSystem, setIsDarkSystem] = useState(systemPrefersDark);

  // Derived, not synced: the account is the source of truth when there is
  // one, and there is no effect copying it into state to fall out of date.
  const accountTheme =
    userId == null ? cached : normalizeTheme(user?.theme);

  const theme =
    chosen && chosen.userId === userId ? chosen.theme : accountTheme;

  // Mirror the account's theme into that account's cache. Without this,
  // the first load on a new device has nothing to read before React runs,
  // so every user who chose a non-default theme gets a frame of the wrong
  // one — which is precisely what the pre-paint script exists to prevent.
  // Writing to storage is an external-system sync, not a setState.
  useEffect(() => {
    if (userId == null) return;
    writeThemeCache(normalizeTheme(user?.theme), userId);
  }, [userId, user?.theme]);

  // The document is stamped before React mounts by the inline script in
  // index.html; this keeps it in step afterwards. Writing an attribute on
  // <html> is exactly the external-system sync an effect is for.
  useEffect(() => {
    applyTheme(theme);
  }, [theme]);

  // "System" means follow the device even while the page is open.
  useEffect(() => {
    if (typeof window === "undefined" || !window.matchMedia) return undefined;

    const query = window.matchMedia("(prefers-color-scheme: dark)");
    const listen = (event) => setIsDarkSystem(event.matches);

    query.addEventListener("change", listen);
    return () => query.removeEventListener("change", listen);
  }, []);

  const setTheme = useCallback(
    async (next) => {
      const value = normalizeTheme(next);

      // Applied first, saved second: the switch is the whole feedback,
      // and a slow network should not make it feel broken.
      setChosen({ userId, theme: value });
      if (userId == null) setCached(value);
      writeThemeCache(value, userId);

      if (userId == null) return { ok: true };

      try {
        await api.put(`/users/${userId}/theme`, { theme: value });
        return { ok: true };
      } catch (error) {
        console.error("Failed to save the theme preference:", error);
        return { ok: false, error };
      }
    },
    [userId],
  );

  const value = useMemo(
    () => ({
      theme,
      setTheme,
      // What the viewer is actually seeing — for a label, never for a
      // rendering decision.
      resolved: effectiveTheme(theme, isDarkSystem),
      systemIsDark: isDarkSystem,
    }),
    [theme, setTheme, isDarkSystem],
  );

  return (
    <ThemeContext.Provider value={value}>{children}</ThemeContext.Provider>
  );
}

export function useTheme() {
  return (
    useContext(ThemeContext) || {
      theme: DEFAULT_THEME,
      setTheme: async () => ({ ok: false }),
      resolved: "light",
      systemIsDark: false,
    }
  );
}
