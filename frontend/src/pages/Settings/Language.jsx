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
    <div className="min-h-screen bg-paper px-6 py-10">
      <div className="mx-auto max-w-4xl">
        {/* Header */}
        <div className="mb-8">
          <BackLink onClick={() => navigate("/settings")} className="mb-4">
            {t("common.backToSettings")}
          </BackLink>

          <div className="flex items-center gap-3">
            <div className="flex h-12 w-12 items-center justify-center rounded-card bg-paper-sunken text-cedar">
              <Languages size={24} />
            </div>

            <div>
              <h1 className="text-title font-bold text-ink">
                {t("language.title")}
              </h1>

              <p className="mt-1 text-small text-ink-secondary">
                {t("language.subtitle")}
              </p>
            </div>
          </div>
        </div>

        {/* Language Settings */}
        <section className="overflow-hidden rounded-card bg-paper-raised shadow-card">
          <div className="border-b border-line-subtle px-6 py-5">
            <h2 className="text-title font-semibold text-ink">
              {t("language.preferredLanguage")}
            </h2>

            <p className="mt-1 text-small text-ink-muted">
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
                  className={`flex w-full cursor-pointer items-center justify-between rounded-card border p-4 text-start transition ${
                    isSelected
                      ? "border-cedar-ring bg-paper-sunken"
                      : "border-line hover:bg-paper"
                  }`}
                >
                  <div>
                    <p className="font-medium text-ink">
                      {t(`language.${language.code === "en"
                        ? "english"
                        : language.code === "ar"
                          ? "arabic"
                          : "french"}`)}
                    </p>

                    <p className="mt-1 text-small text-ink-muted">
                      {language.nativeName}
                    </p>
                  </div>

                  {isSelected && (
                    <div className="flex h-7 w-7 items-center justify-center rounded-pill bg-cedar text-on-cedar">
                      <Check size={17} />
                    </div>
                  )}
                </button>
              );
            })}

            <div className="flex justify-end border-t border-line-subtle pt-6">
              <button
                type="button"
                onClick={handleSaveLanguage}
                className="cursor-pointer rounded-control bg-cedar px-6 py-3 text-small font-semibold text-on-cedar transition hover:bg-cedar-strong"
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