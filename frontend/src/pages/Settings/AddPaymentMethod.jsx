import { useState } from "react";
import { useNavigate } from "react-router-dom";
import { useTranslation } from "react-i18next";
import { CreditCard } from "lucide-react";
import { toast } from "react-toastify";
import BackLink from "../../components/common/BackLink";

import api from "../../services/api";


function AddPaymentMethod() {
  const { t } = useTranslation();
  const navigate = useNavigate();
  // The full card number is never collected — not typed, not held in
  // state, not sent. The customer reads the last four off their own card.
  // See docs/decisions/0024-no-card-data.md.
  const [formData, setFormData] = useState({
    brand: "",
    last4: "",
    expMonth: "",
    expYear: "",
    cardholderName: "",
    is_default: false,
  });
  const [saving, setSaving] = useState(false);

  const thisYear = new Date().getFullYear();
  const years = Array.from({ length: 15 }, (_, index) => thisYear + index);
  const months = Array.from({ length: 12 }, (_, index) => index + 1);

  const handleSubmit = async (event) => {
    event.preventDefault();

    if (!/^\d{4}$/.test(formData.last4)) {
      toast.error(t("paymentMethods.errLastFour"));
      return;
    }

    if (!formData.expMonth || !formData.expYear) {
      toast.error(t("paymentMethods.errExpiry"));
      return;
    }

    if (!formData.cardholderName.trim()) {
      toast.error(t("paymentMethods.errCardholderName"));
      return;
    }

    try {
      setSaving(true);

      await api.post("/payment-methods", {
        type: "card",
        label: formData.cardholderName.trim(),
        brand: formData.brand || null,
        last4: formData.last4,
        exp_month: Number(formData.expMonth),
        exp_year: Number(formData.expYear),
        is_default: formData.is_default,
      });

      toast.success(t("paymentMethods.toastAdded"));
      navigate("/settings/payment-methods");
    } catch (error) {
      console.error("Error adding card:", error);
      toast.error(
        error.response?.data?.message || t("paymentMethods.errAdd"),
      );
    } finally {
      setSaving(false);
    }
  };

  return (
    <div className="min-h-screen bg-gray-50 px-6 py-10">
      <div className="mx-auto max-w-3xl">
        <BackLink
          onClick={() => navigate("/settings/payment-methods")}
          className="mb-4"
        >
          {t("backLink.savedCards")}
        </BackLink>

        <h1 className="text-3xl font-bold text-gray-900">{t("paymentMethods.formAddTitle")}</h1>

        <p className="mt-2 text-sm text-gray-600">
          {t("paymentMethods.formAddSubtitle")}
        </p>

        <form
          onSubmit={handleSubmit}
          className="mt-6 rounded-xl bg-white p-6 shadow-sm"
        >
          <div className="mb-6 flex items-center gap-4 rounded-xl border border-green-600 bg-green-50 p-4">
            <div className="flex h-11 w-11 items-center justify-center rounded-lg bg-white text-green-700">
              <CreditCard size={22} />
            </div>

            <div>
              <p className="font-semibold text-gray-900">{t("paymentMethods.cardBadge")}</p>
              <p className="text-xs text-gray-500">
                {t("paymentMethods.cardBadgeDesc")}
              </p>
            </div>
          </div>

          <div className="space-y-6">
            <p className="rounded-lg bg-gray-50 px-4 py-3 text-sm text-gray-600">
              {t("paymentMethods.noNumberNotice")}
            </p>

            <div className="grid gap-6 sm:grid-cols-2">
              <div>
                <label
                  htmlFor="brand"
                  className="mb-2 block text-sm font-medium text-gray-700"
                >
                  {t("paymentMethods.brand")}
                </label>

                <select
                  id="brand"
                  value={formData.brand}
                  onChange={(event) =>
                    setFormData((previous) => ({
                      ...previous,
                      brand: event.target.value,
                    }))
                  }
                  className="w-full rounded-lg border border-gray-300 px-4 py-3 outline-none focus:border-green-600 focus:ring-2 focus:ring-green-100"
                >
                  <option value="">{t("paymentMethods.brandNone")}</option>
                  <option value="Visa">Visa</option>
                  <option value="Mastercard">Mastercard</option>
                  <option value="Amex">American Express</option>
                </select>
              </div>

              <div>
                <label
                  htmlFor="last4"
                  className="mb-2 block text-sm font-medium text-gray-700"
                >
                  {t("paymentMethods.lastFour")}
                </label>

                {/* Deliberately not autoComplete="cc-number": the browser
                    must not offer to fill a whole card number into a
                    field that accepts four digits. */}
                <input
                  id="last4"
                  type="text"
                  inputMode="numeric"
                  maxLength={4}
                  autoComplete="off"
                  dir="ltr"
                  value={formData.last4}
                  onChange={(event) =>
                    setFormData((previous) => ({
                      ...previous,
                      last4: event.target.value.replace(/\D/g, "").slice(0, 4),
                    }))
                  }
                  placeholder="4242"
                  required
                  className="w-full rounded-lg border border-gray-300 px-4 py-3 outline-none focus:border-green-600 focus:ring-2 focus:ring-green-100"
                />
              </div>

              <div>
                <label
                  htmlFor="expMonth"
                  className="mb-2 block text-sm font-medium text-gray-700"
                >
                  {t("paymentMethods.expiryMonth")}
                </label>

                <select
                  id="expMonth"
                  value={formData.expMonth}
                  onChange={(event) =>
                    setFormData((previous) => ({
                      ...previous,
                      expMonth: event.target.value,
                    }))
                  }
                  required
                  className="w-full rounded-lg border border-gray-300 px-4 py-3 outline-none focus:border-green-600 focus:ring-2 focus:ring-green-100"
                >
                  <option value="">--</option>
                  {months.map((month) => (
                    <option key={month} value={month}>
                      {String(month).padStart(2, "0")}
                    </option>
                  ))}
                </select>
              </div>

              <div>
                <label
                  htmlFor="expYear"
                  className="mb-2 block text-sm font-medium text-gray-700"
                >
                  {t("paymentMethods.expiryYear")}
                </label>

                <select
                  id="expYear"
                  value={formData.expYear}
                  onChange={(event) =>
                    setFormData((previous) => ({
                      ...previous,
                      expYear: event.target.value,
                    }))
                  }
                  required
                  className="w-full rounded-lg border border-gray-300 px-4 py-3 outline-none focus:border-green-600 focus:ring-2 focus:ring-green-100"
                >
                  <option value="">----</option>
                  {years.map((year) => (
                    <option key={year} value={year}>
                      {year}
                    </option>
                  ))}
                </select>
              </div>
            </div>

            <div>
              <label
                htmlFor="cardholderName"
                className="mb-2 block text-sm font-medium text-gray-700"
              >
                {t("paymentMethods.cardholderName")}
              </label>

              <input
                id="cardholderName"
                type="text"
                autoComplete="cc-name"
                value={formData.cardholderName}
                onChange={(event) =>
                  setFormData((previous) => ({
                    ...previous,
                    cardholderName: event.target.value,
                  }))
                }
                placeholder={t("paymentMethods.cardholderNamePlaceholder")}
                required
                className="w-full rounded-lg border border-gray-300 px-4 py-3 outline-none focus:border-green-600 focus:ring-2 focus:ring-green-100"
              />
            </div>

            <label className="flex cursor-pointer items-start gap-3 rounded-lg border border-gray-200 p-4">
              <input
                type="checkbox"
                checked={formData.is_default}
                onChange={(event) =>
                  setFormData((previous) => ({
                    ...previous,
                    is_default: event.target.checked,
                  }))
                }
                className="mt-1 h-4 w-4 rounded border-gray-300 text-green-700 focus:ring-green-600"
              />

              <span>
                <span className="block text-sm font-medium text-gray-800">
                  {t("paymentMethods.setDefaultCard")}
                </span>
                <span className="mt-1 block text-xs text-gray-600">
                  {t("paymentMethods.setDefaultCardDesc")}
                </span>
              </span>
            </label>

            <div className="flex justify-end gap-3 border-t border-gray-100 pt-6">
              <button
                type="button"
                onClick={() => navigate("/settings/payment-methods")}
                disabled={saving}
                className="rounded-lg border border-gray-300 px-5 py-3 text-sm font-medium text-gray-700 hover:bg-gray-50 disabled:opacity-50"
              >
                {t("paymentMethods.cancel")}
              </button>

              <button
                type="submit"
                disabled={saving}
                className="cursor-pointer rounded-lg bg-green-700 px-5 py-3 text-sm font-semibold text-white hover:bg-green-800 disabled:opacity-50"
              >
                {saving ? t("common.working") : t("paymentMethods.saveAdd")}
              </button>
            </div>
          </div>
        </form>
      </div>
    </div>
  );
}

export default AddPaymentMethod;
