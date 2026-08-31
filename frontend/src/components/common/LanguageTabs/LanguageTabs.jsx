import { useTranslation } from "react-i18next";

import { SUPPORTED_LANGUAGES } from "../../../i18n/i18n";

const LABEL_KEY = {
  en: "language.english",
  ar: "language.arabic",
  fr: "language.french",
};

/**
 * Tab bar for entering a field in each of the three languages.
 *
 * `active`   — the currently selected language code
 * `onSelect` — (lang) => void
 * `filled`   — { en, ar, fr } booleans; ar / fr show a dot when a
 *              translation has been entered. English carries a required mark.
 */
function LanguageTabs({ active, onSelect, filled = {} }) {
  const { t } = useTranslation();

  return (
    <div
      role="tablist"
      className="flex gap-1 border-b border-gray-200"
    >
      {SUPPORTED_LANGUAGES.map((lang) => {
        const isActive = lang === active;
        const isEnglish = lang === "en";
        const isFilled = Boolean(filled[lang]);

        return (
          <button
            key={lang}
            type="button"
            role="tab"
            aria-selected={isActive}
            onClick={() => onSelect(lang)}
            className={`-mb-px flex items-center gap-1.5 border-b-2 px-3 py-2 text-xs font-medium transition ${
              isActive
                ? "border-emerald-600 text-emerald-700"
                : "border-transparent text-gray-500 hover:text-gray-700"
            }`}
          >
            {t(LABEL_KEY[lang])}
            {isEnglish ? (
              <span
                className="text-red-500"
                title={t("translationTabs.englishRequired")}
                aria-label={t("translationTabs.englishRequired")}
              >
                *
              </span>
            ) : (
              <span
                className={`h-1.5 w-1.5 rounded-full ${
                  isFilled ? "bg-emerald-500" : "bg-gray-300"
                }`}
                title={
                  isFilled
                    ? t("translationTabs.filled")
                    : t("translationTabs.notFilled")
                }
                aria-label={
                  isFilled
                    ? t("translationTabs.filled")
                    : t("translationTabs.notFilled")
                }
              />
            )}
          </button>
        );
      })}
    </div>
  );
}

export default LanguageTabs;
