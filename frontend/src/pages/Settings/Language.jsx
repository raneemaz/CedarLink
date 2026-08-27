import { useEffect, useState } from "react";
import { useNavigate } from "react-router-dom";
import { Check, Languages } from "lucide-react";
import { toast } from "react-toastify";
import { useTranslation } from "react-i18next";

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

  useEffect(() => {
    const currentLanguage =
      localStorage.getItem("cedarlink_language") || "en";

    document.documentElement.lang = currentLanguage;
    document.documentElement.dir =
      currentLanguage === "ar" ? "rtl" : "ltr";
  }, []);

  const handleSaveLanguage = () => {
    localStorage.setItem("cedarlink_language", selectedLanguage);

    i18n.changeLanguage(selectedLanguage);

    document.documentElement.lang = selectedLanguage;
    document.documentElement.dir =
      selectedLanguage === "ar" ? "rtl" : "ltr";

    toast.success(t("language.saved"));
  };

  return (
    <div className="min-h-screen bg-gray-50 px-6 py-10">
      <div className="mx-auto max-w-4xl">
        {/* Header */}
        <div className="mb-8">
          <button
            onClick={() => navigate("/settings")}
            className="mb-4 cursor-pointer text-sm text-green-700 hover:underline"
          >
            {t("common.backToSettings")}
          </button>

          <div className="flex items-center gap-3">
            <div className="flex h-12 w-12 items-center justify-center rounded-xl bg-emerald-50 text-emerald-700">
              <Languages size={24} />
            </div>

            <div>
              <h1 className="text-3xl font-bold text-gray-900">
                {t("language.title")}
              </h1>

              <p className="mt-1 text-sm text-gray-600">
                {t("language.subtitle")}
              </p>
            </div>
          </div>
        </div>

        {/* Language Settings */}
        <section className="overflow-hidden rounded-2xl bg-white shadow-sm">
          <div className="border-b border-gray-100 px-6 py-5">
            <h2 className="text-xl font-semibold text-gray-900">
              {t("language.preferredLanguage")}
            </h2>

            <p className="mt-1 text-sm text-gray-500">
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
                  className={`flex w-full cursor-pointer items-center justify-between rounded-xl border p-4 text-left transition ${
                    isSelected
                      ? "border-green-600 bg-green-50"
                      : "border-gray-200 hover:bg-gray-50"
                  }`}
                >
                  <div>
                    <p className="font-medium text-gray-900">
                      {t(`language.${language.code === "en"
                        ? "english"
                        : language.code === "ar"
                          ? "arabic"
                          : "french"}`)}
                    </p>

                    <p className="mt-1 text-sm text-gray-500">
                      {language.nativeName}
                    </p>
                  </div>

                  {isSelected && (
                    <div className="flex h-7 w-7 items-center justify-center rounded-full bg-green-700 text-white">
                      <Check size={17} />
                    </div>
                  )}
                </button>
              );
            })}

            <div className="flex justify-end border-t border-gray-100 pt-6">
              <button
                type="button"
                onClick={handleSaveLanguage}
                className="cursor-pointer rounded-lg bg-green-700 px-6 py-3 text-sm font-semibold text-white transition hover:bg-green-800"
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