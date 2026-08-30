import { useEffect, useState } from "react";
import { useNavigate } from "react-router-dom";
import { Check, Coins } from "lucide-react";
import { toast } from "react-toastify";
import { useTranslation } from "react-i18next";

import api from "../../services/api";
import { useCurrency } from "../../context/CurrencyContext";
import BackLink from "../../components/common/BackLink";

const currencies = [
  { code: "USD", labelKey: "usd", sample: "$" },
  { code: "LBP", labelKey: "lbp", sample: "ل.ل" },
];

function getStoredUser() {
  const savedUser = localStorage.getItem("user");

  if (!savedUser || savedUser === "undefined") {
    return null;
  }

  try {
    return JSON.parse(savedUser);
  } catch {
    localStorage.removeItem("user");
    return null;
  }
}

function Currency() {
  const navigate = useNavigate();
  const { t } = useTranslation();
  const { currency, setCurrency } = useCurrency();

  const [selectedCurrency, setSelectedCurrency] = useState(currency);
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);

  useEffect(() => {
    const storedUser = getStoredUser();

    if (!storedUser?.id) {
      toast.error(t("currency.loadError"));
      setLoading(false);
      return;
    }

    const fetchCurrency = async () => {
      try {
        const response = await api.get(`/users/${storedUser.id}`);
        const serverCurrency = response.data?.user?.currency || "USD";

        setSelectedCurrency(serverCurrency);
      } catch (error) {
        console.error("Failed to load currency preference:", error);
        toast.error(t("currency.loadError"));
      } finally {
        setLoading(false);
      }
    };

    fetchCurrency();
  }, [t]);

  const handleSaveCurrency = async () => {
    const storedUser = getStoredUser();

    if (!storedUser?.id) {
      toast.error(t("currency.loadError"));
      return;
    }

    setSaving(true);

    try {
      const response = await api.put(`/users/${storedUser.id}/currency`, {
        currency: selectedCurrency,
      });

      const savedCurrency =
        response.data?.user?.currency || selectedCurrency;

      // Keep the stored user blob and the currency context in sync.
      localStorage.setItem(
        "user",
        JSON.stringify({ ...storedUser, currency: savedCurrency }),
      );
      setCurrency(savedCurrency);

      toast.success(t("currency.saved"));
    } catch (error) {
      console.error("Failed to update currency preference:", error);
      toast.error(
        error.response?.data?.message || t("currency.saveError"),
      );
    } finally {
      setSaving(false);
    }
  };

  return (
    <div className="min-h-screen bg-gray-50 px-6 py-10">
      <div className="mx-auto max-w-4xl">
        {/* Header */}
        <div className="mb-8">
          <BackLink onClick={() => navigate("/settings")} className="mb-4">
            {t("common.backToSettings")}
          </BackLink>

          <div className="flex items-center gap-3">
            <div className="flex h-12 w-12 items-center justify-center rounded-xl bg-emerald-50 text-emerald-700">
              <Coins size={24} />
            </div>

            <div>
              <h1 className="text-3xl font-bold text-gray-900">
                {t("currency.title")}
              </h1>

              <p className="mt-1 text-sm text-gray-600">
                {t("currency.subtitle")}
              </p>
            </div>
          </div>
        </div>

        {/* Currency Settings */}
        <section className="overflow-hidden rounded-2xl bg-white shadow-sm">
          <div className="border-b border-gray-100 px-6 py-5">
            <h2 className="text-xl font-semibold text-gray-900">
              {t("currency.preferredCurrency")}
            </h2>

            <p className="mt-1 text-sm text-gray-500">
              {t("currency.description")}
            </p>
          </div>

          <div className="space-y-3 px-6 py-6">
            {loading ? (
              <p className="text-sm text-gray-500">
                {t("currency.loading")}
              </p>
            ) : (
              <>
                {currencies.map((option) => {
                  const isSelected = selectedCurrency === option.code;

                  return (
                    <button
                      key={option.code}
                      type="button"
                      onClick={() => setSelectedCurrency(option.code)}
                      className={`flex w-full cursor-pointer items-center justify-between rounded-xl border p-4 text-start transition ${
                        isSelected
                          ? "border-green-600 bg-green-50"
                          : "border-gray-200 hover:bg-gray-50"
                      }`}
                    >
                      <div>
                        <p className="font-medium text-gray-900">
                          {t(`currency.${option.labelKey}`)}
                        </p>

                        <p className="mt-1 text-sm text-gray-500">
                          {option.code} · {option.sample}
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

                <p className="pt-2 text-xs text-gray-400">
                  {t("currency.approxNote")}
                </p>

                <div className="flex justify-end border-t border-gray-100 pt-6">
                  <button
                    type="button"
                    onClick={handleSaveCurrency}
                    disabled={saving}
                    className="cursor-pointer rounded-lg bg-green-700 px-6 py-3 text-sm font-semibold text-white transition hover:bg-green-800 disabled:cursor-not-allowed disabled:opacity-60"
                  >
                    {saving
                      ? t("currency.saving")
                      : t("currency.saveCurrency")}
                  </button>
                </div>
              </>
            )}
          </div>
        </section>
      </div>
    </div>
  );
}

export default Currency;
