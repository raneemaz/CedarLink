import { useState } from "react";
import { useNavigate } from "react-router-dom";
import { Check, Languages } from "lucide-react";
import { toast } from "react-toastify";
import { useTranslation } from "react-i18next";
import BackLink from "../../components/common/BackLink";

function Language() {
  const navigate = useNavigate();
  const { t, i18n } = useTranslation();

  const [selectedLanguage, setSelectedLanguage] = useState(
    localStorage.getItem("cedarlink_language") || "en",
  );

  const languages = [
    {
      code: "en",
      name: "English",
      nativeName: "English",
    },
    {
      code: "ar",
      name: "Arabic",
      nativeName: "العربية",
    },
    {
      code: "fr",
      name: "French",
      nativeName: "Français",
    },
  ];

  const handleSaveLanguage = () => {
    try {
      localStorage.setItem("cedarlink_language", selectedLanguage);
    } catch {
      /* storage unavailable — the switch below still applies for this session */
    }

    // i18n fires "languageChanged", which updates <html dir/lang> globally
    // (see i18n.js). No need to touch the document here.
    i18n.changeLanguage(selectedLanguage);

    toast.success(t("language.saved"));
  };

  return (
    <div className="min-h-screen bg-surface px-6 py-10">
      <div className="mx-auto max-w-4xl">
        {/* Header */}
        <div className="mb-8">
          <BackLink onClick={() => navigate("/settings")} className="mb-4">
            {t("common.backToSettings")}
          </BackLink>

          <div className="flex items-center gap-3">
            <div className="flex h-12 w-12 items-center justify-center rounded-xl bg-brand-subtle text-brand">
              <Languages size={24} />
            </div>

            <div>
              <h1 className="text-3xl font-bold text-text-primary">
                {t("language.title")}
              </h1>

              <p className="mt-1 text-sm text-text-secondary">
                {t("language.subtitle")}
              </p>
            </div>
          </div>
        </div>

        {/* Language Settings */}
        <section className="overflow-hidden rounded-2xl bg-surface-raised shadow-sm">
          <div className="border-b border-border-subtle px-6 py-5">
            <h2 className="text-xl font-semibold text-text-primary">
              {t("language.preferredLanguage")}
            </h2>

            <p className="mt-1 text-sm text-text-muted">
              {t("language.description")}
            </p>
          </div>

          <div className="space-y-3 px-6 py-6">
            {languages.map((language) => {
              const isSelected = selectedLanguage === language.code;

              return (
                <button
                  key={language.code}
                  type="button"
                  onClick={() => setSelectedLanguage(language.code)}
                  className={`flex w-full cursor-pointer items-center justify-between rounded-xl border p-4 text-start transition ${
                    isSelected
                      ? "border-brand-ring bg-brand-subtle"
                      : "border-border hover:bg-surface"
                  }`}
                >
                  <div>
                    <p className="font-medium text-text-primary">
                      {t(`language.${language.code === "en"
                        ? "english"
                        : language.code === "ar"
                          ? "arabic"
                          : "french"}`)}
                    </p>

                    <p className="mt-1 text-sm text-text-muted">
                      {language.nativeName}
                    </p>
                  </div>

                  {isSelected && (
                    <div className="flex h-7 w-7 items-center justify-center rounded-full bg-brand text-on-brand">
                      <Check size={17} />
                    </div>
                  )}
                </button>
              );
            })}

            <div className="flex justify-end border-t border-border-subtle pt-6">
              <button
                type="button"
                onClick={handleSaveLanguage}
                className="cursor-pointer rounded-lg bg-brand px-6 py-3 text-sm font-semibold text-on-brand transition hover:bg-brand-strong"
              >
                {t("language.saveLanguage")}
              </button>
            </div>
          </div>
        </section>
      </div>
    </div>
  );
}

export default Language;