import { useEffect, useState } from "react";
import { useNavigate } from "react-router-dom";
import { ShoppingBag } from "lucide-react";
import { toast } from "react-toastify";
import { useTranslation } from "react-i18next";

import api from "../../services/api";
import Toggle from "../../components/common/Toggle/Toggle";
import { lebanonLocations } from "../../data/lebanonLocations";
import BackLink from "../../components/common/BackLink";

const DEFAULT_PREFERENCES = {
  autofill_default_address: true,
  preferred_payment_method: "cash_on_delivery",
  default_delivery_city: null,
  hide_out_of_stock: false,
};

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

function ShoppingPreferences() {
  const navigate = useNavigate();
  const { t } = useTranslation();

  const [preferences, setPreferences] = useState(DEFAULT_PREFERENCES);
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);

  useEffect(() => {
    const storedUser = getStoredUser();

    if (!storedUser?.id) {
      toast.error(t("shoppingPreferences.loadError"));
      setLoading(false);
      return;
    }

    const fetchPreferences = async () => {
      try {
        const response = await api.get(
          `/users/${storedUser.id}/shopping-preferences`,
        );
        const server = response.data?.shopping_preferences;

        if (server) {
          setPreferences({ ...DEFAULT_PREFERENCES, ...server });
        }
      } catch (error) {
        console.error("Failed to load shopping preferences:", error);
        toast.error(t("shoppingPreferences.loadError"));
      } finally {
        setLoading(false);
      }
    };

    fetchPreferences();
  }, [t]);

  const setField = (key, value) => {
    setPreferences((previous) => ({ ...previous, [key]: value }));
  };

  const handleSave = async () => {
    const storedUser = getStoredUser();

    if (!storedUser?.id) {
      toast.error(t("shoppingPreferences.loadError"));
      return;
    }

    setSaving(true);

    try {
      const response = await api.put(
        `/users/${storedUser.id}/shopping-preferences`,
        {
          autofill_default_address: preferences.autofill_default_address,
          preferred_payment_method: preferences.preferred_payment_method,
          default_delivery_city: preferences.default_delivery_city || null,
          hide_out_of_stock: preferences.hide_out_of_stock,
        },
      );

      const saved =
        response.data?.user?.shopping_preferences || preferences;

      setPreferences({ ...DEFAULT_PREFERENCES, ...saved });
      toast.success(t("shoppingPreferences.saved"));
    } catch (error) {
      console.error("Failed to update shopping preferences:", error);
      toast.error(
        error.response?.data?.message ||
          t("shoppingPreferences.saveError"),
      );
    } finally {
      setSaving(false);
    }
  };

  return (
    <div className="min-h-screen bg-gray-50 px-6 py-10">
      <div className="mx-auto max-w-4xl">
        <div className="mb-8">
          <BackLink onClick={() => navigate("/settings")} className="mb-4">
            {t("common.backToSettings")}
          </BackLink>

          <div className="flex items-center gap-3">
            <div className="flex h-12 w-12 items-center justify-center rounded-xl bg-emerald-50 text-emerald-700">
              <ShoppingBag size={24} />
            </div>

            <div>
              <h1 className="text-3xl font-bold text-gray-900">
                {t("shoppingPreferences.title")}
              </h1>
              <p className="mt-1 text-sm text-gray-600">
                {t("shoppingPreferences.subtitle")}
              </p>
            </div>
          </div>
        </div>

        {loading ? (
          <p className="text-sm text-gray-500">
            {t("shoppingPreferences.loading")}
          </p>
        ) : (
          <div className="space-y-6">
            <section className="overflow-hidden rounded-2xl bg-white shadow-sm">
              <div className="border-b border-gray-100 px-6 py-5">
                <h2 className="text-xl font-semibold text-gray-900">
                  {t("shoppingPreferences.checkoutSection")}
                </h2>
                <p className="mt-1 text-sm text-gray-500">
                  {t("shoppingPreferences.checkoutSectionDesc")}
                </p>
              </div>

              <div className="divide-y divide-gray-100 px-6">
                <Toggle
                  checked={preferences.autofill_default_address}
                  onChange={(v) => setField("autofill_default_address", v)}
                  label={t("shoppingPreferences.autofillLabel")}
                  description={t("shoppingPreferences.autofillDesc")}
                />

                <div className="py-4">
                  <p className="font-medium text-gray-900">
                    {t("shoppingPreferences.paymentLabel")}
                  </p>
                  <p className="mt-1 text-sm text-gray-500">
                    {t("shoppingPreferences.paymentDesc")}
                  </p>

                  <div className="mt-3 space-y-2">
                    {["cash_on_delivery", "card"].map((method) => (
                      <label
                        key={method}
                        className={`flex cursor-pointer items-center gap-3 rounded-lg border p-3 text-sm transition ${
                          preferences.preferred_payment_method === method
                            ? "border-green-600 bg-green-50"
                            : "border-gray-200 hover:bg-gray-50"
                        }`}
                      >
                        <input
                          type="radio"
                          name="preferred_payment_method"
                          value={method}
                          checked={
                            preferences.preferred_payment_method === method
                          }
                          onChange={() =>
                            setField("preferred_payment_method", method)
                          }
                          className="h-4 w-4"
                        />
                        {t(
                          method === "card"
                            ? "shoppingPreferences.paymentCard"
                            : "shoppingPreferences.paymentCod",
                        )}
                      </label>
                    ))}
                  </div>
                </div>

                <div className="py-4">
                  <label
                    htmlFor="default_delivery_city"
                    className="block font-medium text-gray-900"
                  >
                    {t("shoppingPreferences.cityLabel")}
                  </label>
                  <p className="mt-1 text-sm text-gray-500">
                    {t("shoppingPreferences.cityDesc")}
                  </p>

                  <select
                    id="default_delivery_city"
                    value={preferences.default_delivery_city || ""}
                    onChange={(e) =>
                      setField(
                        "default_delivery_city",
                        e.target.value || null,
                      )
                    }
                    className="mt-3 w-full rounded-lg border border-gray-300 bg-white px-4 py-2.5 text-sm outline-none focus:border-green-600 focus:ring-2 focus:ring-green-100"
                  >
                    <option value="">
                      {t("shoppingPreferences.cityNone")}
                    </option>
                    {lebanonLocations.map((location) => (
                      <option
                        key={location.governorate}
                        value={location.governorate}
                      >
                        {location.governorate}
                      </option>
                    ))}
                  </select>
                </div>
              </div>
            </section>

            <section className="overflow-hidden rounded-2xl bg-white shadow-sm">
              <div className="border-b border-gray-100 px-6 py-5">
                <h2 className="text-xl font-semibold text-gray-900">
                  {t("shoppingPreferences.browsingSection")}
                </h2>
                <p className="mt-1 text-sm text-gray-500">
                  {t("shoppingPreferences.browsingSectionDesc")}
                </p>
              </div>

              <div className="px-6">
                <Toggle
                  checked={preferences.hide_out_of_stock}
                  onChange={(v) => setField("hide_out_of_stock", v)}
                  label={t("shoppingPreferences.hideOosLabel")}
                  description={t("shoppingPreferences.hideOosDesc")}
                />
              </div>
            </section>

            <div className="flex justify-end">
              <button
                type="button"
                onClick={handleSave}
                disabled={saving}
                className="cursor-pointer rounded-lg bg-green-700 px-6 py-3 text-sm font-semibold text-white transition hover:bg-green-800 disabled:cursor-not-allowed disabled:opacity-60"
              >
                {saving
                  ? t("shoppingPreferences.saving")
                  : t("shoppingPreferences.save")}
              </button>
            </div>
          </div>
        )}
      </div>
    </div>
  );
}

export default ShoppingPreferences;
