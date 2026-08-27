import i18n from "i18next";
import { initReactI18next } from "react-i18next";

import en from "./en.json";
import ar from "./ar.json";
import fr from "./fr.json";

const savedLanguage =
  localStorage.getItem("cedarlink_language") || "en";

i18n.use(initReactI18next).init({
  resources: {
    en: {
      translation: en,
    },
    ar: {
      translation: ar,
    },
    fr: {
      translation: fr,
    },
  },

  lng: savedLanguage,
  fallbackLng: "en",

  interpolation: {
    escapeValue: false,
  },
});

export default i18n;