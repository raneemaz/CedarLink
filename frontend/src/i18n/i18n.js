import i18n from "i18next";
import { initReactI18next } from "react-i18next";

import en from "./en.json";
import ar from "./ar.json";
import fr from "./fr.json";

export const SUPPORTED_LANGUAGES = ["en", "ar", "fr"];
const RTL_LANGUAGES = ["ar"];
const STORAGE_KEY = "cedarlink_language";

export function isRtl(language) {
  return RTL_LANGUAGES.includes(language);
}

/**
 * Keep <html lang> and <html dir> in step with the active language — on
 * first load and on every switch. index.html runs the same logic inline so
 * the first paint is already correctly oriented on a hard reload.
 */
export function applyDocumentDirection(language) {
  const root = document.documentElement;
  root.lang = language;
  root.dir = isRtl(language) ? "rtl" : "ltr";
}

function detectInitialLanguage() {
  let saved = null;
  try {
    saved = localStorage.getItem(STORAGE_KEY);
  } catch {
    /* storage unavailable */
  }
  if (saved && SUPPORTED_LANGUAGES.includes(saved)) {
    return saved;
  }

  // First visit: take the browser's preference, fall back to English. Once
  // chosen it is persisted, so a later profile change always wins.
  const fromBrowser = (navigator.languages || [navigator.language || ""])
    .map((tag) => String(tag).toLowerCase().split("-")[0])
    .find((base) => SUPPORTED_LANGUAGES.includes(base));

  const chosen = fromBrowser || "en";
  try {
    localStorage.setItem(STORAGE_KEY, chosen);
  } catch {
    /* storage unavailable */
  }
  return chosen;
}

const initialLanguage = detectInitialLanguage();

i18n.use(initReactI18next).init({
  resources: {
    en: { translation: en },
    ar: { translation: ar },
    fr: { translation: fr },
  },
  lng: initialLanguage,
  fallbackLng: "en",
  supportedLngs: SUPPORTED_LANGUAGES,
  interpolation: {
    escapeValue: false,
  },
});

applyDocumentDirection(initialLanguage);
i18n.on("languageChanged", applyDocumentDirection);

export default i18n;
