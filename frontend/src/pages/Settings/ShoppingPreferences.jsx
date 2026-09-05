import { useEffect, useState } from "react";
import { useNavigate } from "react-router-dom";
import { ShoppingBag } from "lucide-react";
import { toast } from "react-toastify";
import { useTranslation } from "react-i18next";

import api from "../../services/api";
import Toggle from "../../components/common/Toggle/Toggle";
import { lebanonLocations } from "../../data/lebanonLocations";
import BackLink from "../../components/common/BackLink";
import { localizedField } from "../../utils/localize";

const DEFAULT_PREFERENCES = {
  autofill_default_address: true,
  preferred_payment_method: "cash_on_delivery",
  default_delivery_city: null,
  hide_out_of_stock: false,
  interest_category_ids: [],
};

// Mirrors shopping_preferences_service.MAX_INTERESTS. The server is the
// authority; this only keeps the form from offering a save it will refuse.
const MAX_INTERESTS = 5;

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
  const { t, i18n } = useTranslation();

  const [preferences, setPreferences] = useState(DEFAULT_PREFERENCES);
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [categories, setCategories] = useState([]);

  // Everything happens inside the async body, so nothing sets state
  // synchronously while the effect is running.
  useEffect(() => {
    let cancelled = false;

    (async () => {
      const storedUser = getStoredUser();

      if (!storedUser?.id) {
        if (!cancelled) {
          toast.error(t("shoppingPreferences.loadError"));
          setLoading(false);
        }
        return;
      }

      try {
        const [prefsResponse, categoriesResponse] = await Promise.all([
          api.get(`/users/${storedUser.id}/shopping-preferences`),
          api.get("/categories"),
        ]);

        if (cancelled) return;

        const server = prefsResponse.data?.shopping_preferences;

        if (server) {
          setPreferences({ ...DEFAULT_PREFERENCES, ...server });
        }

        setCategories(categoriesResponse.data || []);
      } catch (error) {
        console.error("Failed to load shopping preferences:", error);
        if (!cancelled) toast.error(t("shoppingPreferences.loadError"));
      } finally {
        if (!cancelled) setLoading(false);
      }
    })();

    return () => {
      cancelled = true;
    };
  }, [t]);

  const setField = (key, value) => {
    setPreferences((previous) => ({ ...previous, [key]: value }));
  };

  const interests = preferences.interest_category_ids || [];

  // Selection order is meaningful — it is the order the home page uses —
  // so a newly ticked category goes on the end rather than sorting in.
  const toggleInterest = (categoryId) => {
    setPreferences((previous) => {
      const current = previous.interest_category_ids || [];

      if (current.includes(categoryId)) {
        return {
          ...previous,
          interest_category_ids: current.filter((id) => id !== categoryId),
        };
      }

      if (current.length >= MAX_INTERESTS) return previous;

      return {
        ...previous,
        interest_category_ids: [...current, categoryId],
      };
    });
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
          interest_category_ids: preferences.interest_category_ids || [],
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
    <div className="min-h-screen bg-surface px-6 py-10">
      <div className="mx-auto max-w-4xl">
        <div className="mb-8">
          <BackLink onClick={() => navigate("/settings")} className="mb-4">
            {t("common.backToSettings")}
          </BackLink>

          <div className="flex items-center gap-3">
            <div className="flex h-12 w-12 items-center justify-center rounded-xl bg-brand-subtle text-brand">
              <ShoppingBag size={24} />
            </div>

            <div>
              <h1 className="text-3xl font-bold text-text-primary">
                {t("shoppingPreferences.title")}
              </h1>
              <p className="mt-1 text-sm text-text-secondary">
                {t("shoppingPreferences.subtitle")}
              </p>
            </div>
          </div>
        </div>

        {loading ? (
          <p className="text-sm text-text-muted">
            {t("shoppingPreferences.loading")}
          </p>
        ) : (
          <div className="space-y-6">
            <section className="overflow-hidden rounded-2xl bg-surface-raised shadow-sm">
              <div className="border-b border-border-subtle px-6 py-5">
                <h2 className="text-xl font-semibold text-text-primary">
                  {t("shoppingPreferences.checkoutSection")}
                </h2>
                <p className="mt-1 text-sm text-text-muted">
                  {t("shoppingPreferences.checkoutSectionDesc")}
                </p>
              </div>

              <div className="divide-y divide-border-subtle px-6">
                <Toggle
                  checked={preferences.autofill_default_address}
                  onChange={(v) => setField("autofill_default_address", v)}
                  label={t("shoppingPreferences.autofillLabel")}
                  description={t("shoppingPreferences.autofillDesc")}
                />

                <div className="py-4">
                  <p className="font-medium text-text-primary">
                    {t("shoppingPreferences.paymentLabel")}
                  </p>
                  <p className="mt-1 text-sm text-text-muted">
                    {t("shoppingPreferences.paymentDesc")}
                  </p>

                  <div className="mt-3 space-y-2">
                    {["cash_on_delivery", "card"].map((method) => (
                      <label
                        key={method}
                        className={`flex cursor-pointer items-center gap-3 rounded-lg border p-3 text-sm transition ${
                          preferences.preferred_payment_method === method
                            ? "border-brand-ring bg-brand-subtle"
                            : "border-border hover:bg-surface"
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
                    className="block font-medium text-text-primary"
                  >
                    {t("shoppingPreferences.cityLabel")}
                  </label>
                  <p className="mt-1 text-sm text-text-muted">
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
                    className="mt-3 w-full rounded-lg border border-border-strong bg-surface-raised px-4 py-2.5 text-sm outline-none focus:border-brand-ring focus:ring-2 focus:ring-brand-tint"
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

            {/* Interests — stated, never inferred. The home page leads
                with these; nothing here is derived from what the customer
                has browsed or bought, because none of that is recorded. */}
            <section className="overflow-hidden rounded-2xl bg-surface-raised shadow-sm">
              <div className="border-b border-border-subtle px-6 py-5">
                <h2 className="text-xl font-semibold text-text-primary">
                  {t("shoppingPreferences.interestsSection")}
                </h2>
                <p className="mt-1 text-sm text-text-muted">
                  {t("shoppingPreferences.interestsSectionDesc")}
                </p>
              </div>

              <div className="px-6 py-5">
                <div className="mb-4 flex flex-wrap items-center justify-between gap-2">
                  <p className="text-sm text-text-secondary">
                    {t("shoppingPreferences.interestsChosen", {
                      count: interests.length,
                      max: MAX_INTERESTS,
                    })}
                  </p>

                  {interests.length > 0 && (
                    <button
                      type="button"
                      onClick={() => setField("interest_category_ids", [])}
                      className="cursor-pointer text-sm font-medium text-brand hover:underline"
                    >
                      {t("shoppingPreferences.interestsClear")}
                    </button>
                  )}
                </div>

                {categories.length === 0 ? (
                  <p className="text-sm text-text-muted">
                    {t("shoppingPreferences.interestsNone")}
                  </p>
                ) : (
                  <div className="flex flex-wrap gap-2">
                    {categories.map((category) => {
                      const chosen = interests.includes(category.id);
                      const rank = interests.indexOf(category.id) + 1;
                      const full =
                        !chosen && interests.length >= MAX_INTERESTS;

                      return (
                        <button
                          key={category.id}
                          type="button"
                          onClick={() => toggleInterest(category.id)}
                          disabled={full}
                          aria-pressed={chosen}
                          className={`inline-flex cursor-pointer items-center gap-2 rounded-full border px-4 py-2 text-sm font-medium transition disabled:cursor-not-allowed disabled:opacity-40 ${
                            chosen
                              ? "border-brand bg-brand text-on-brand"
                              : "border-border-strong bg-surface-raised text-text-body hover:bg-surface"
                          }`}
                        >
                          {chosen && (
                            <span className="inline-flex h-5 w-5 items-center justify-center rounded-full bg-on-brand/25 text-xs">
                              {rank}
                            </span>
                          )}
                          {localizedField(category, "name", i18n.language)}
                        </button>
                      );
                    })}
                  </div>
                )}

                <p className="mt-4 text-xs text-text-muted">
                  {t("shoppingPreferences.interestsHint")}
                </p>
              </div>
            </section>

            <section className="overflow-hidden rounded-2xl bg-surface-raised shadow-sm">
              <div className="border-b border-border-subtle px-6 py-5">
                <h2 className="text-xl font-semibold text-text-primary">
                  {t("shoppingPreferences.browsingSection")}
                </h2>
                <p className="mt-1 text-sm text-text-muted">
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
                className="cursor-pointer rounded-lg bg-brand px-6 py-3 text-sm font-semibold text-on-brand transition hover:bg-brand-strong disabled:cursor-not-allowed disabled:opacity-60"
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
