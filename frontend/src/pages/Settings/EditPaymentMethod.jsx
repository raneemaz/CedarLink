import { useEffect, useState } from "react";
import { useNavigate, useParams } from "react-router-dom";
import { useTranslation } from "react-i18next";
import { CreditCard } from "lucide-react";
import { toast } from "react-toastify";
import BackLink from "../../components/common/BackLink";

import api from "../../services/api";


function EditPaymentMethod() {
  const { id } = useParams();
  const { t } = useTranslation();
  const navigate = useNavigate();
  const [existingLast4, setExistingLast4] = useState("");
  const [existingBrand, setExistingBrand] = useState("");
  // No card number, here or anywhere else on the client — "replace the
  // card number" is now "correct the last four", because the number was
  // never on this page to begin with.
  // See docs/decisions/0024-no-card-data.md.
  const [formData, setFormData] = useState({
    brand: "",
    last4: "",
    expMonth: "",
    expYear: "",
    label: "",
    is_default: false,
  });
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);

  const thisYear = new Date().getFullYear();
  const years = Array.from({ length: 15 }, (_, index) => thisYear + index);
  const months = Array.from({ length: 12 }, (_, index) => index + 1);

  useEffect(() => {
    const fetchCard = async () => {
      try {
        const response = await api.get(`/payment-methods/${id}`);
        const paymentMethod = response.data.payment_method;

        if (paymentMethod.type !== "card") {
          throw new Error("card-type-required");
        }

        setExistingLast4(paymentMethod.last4 || "");
        setExistingBrand(paymentMethod.brand || "");
        setFormData({
          brand: paymentMethod.brand || "",
          last4: paymentMethod.last4 || "",
          expMonth: paymentMethod.exp_month
            ? String(paymentMethod.exp_month)
            : "",
          expYear: paymentMethod.exp_year
            ? String(paymentMethod.exp_year)
            : "",
          label: paymentMethod.label || "",
          is_default: Boolean(paymentMethod.is_default),
        });
      } catch (error) {
        console.error("Error loading card:", error);
        toast.error(
          error.response?.data?.message || t("paymentMethods.errLoadCard"),
        );
        navigate("/settings/payment-methods");
      } finally {
        setLoading(false);
      }
    };

    fetchCard();
  }, [id, navigate, t]);

  const handleSubmit = async (event) => {
    event.preventDefault();

    if (!formData.label.trim()) {
      toast.error(t("paymentMethods.errCardholderName"));
      return;
    }

    if (!/^\d{4}$/.test(formData.last4)) {
      toast.error(t("paymentMethods.errLastFour"));
      return;
    }

    if (!formData.expMonth || !formData.expYear) {
      toast.error(t("paymentMethods.errExpiry"));
      return;
    }

    try {
      setSaving(true);

      await api.put(`/payment-methods/${id}`, {
        type: "card",
        label: formData.label.trim(),
        brand: formData.brand || existingBrand || null,
        last4: formData.last4,
        exp_month: Number(formData.expMonth),
        exp_year: Number(formData.expYear),
        is_default: formData.is_default,
      });

      toast.success(t("paymentMethods.toastUpdated"));
      navigate("/settings/payment-methods");
    } catch (error) {
      console.error("Error updating card:", error);
      toast.error(
        error.response?.data?.message || t("paymentMethods.errUpdate"),
      );
    } finally {
      setSaving(false);
    }
  };

  if (loading) {
    return (
      <div className="min-h-screen bg-paper px-6 py-10">
        <div className="mx-auto max-w-3xl text-ink-muted">
          {t("paymentMethods.formLoading")}
        </div>
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-paper px-6 py-10">
      <div className="mx-auto max-w-3xl">
        <BackLink
          onClick={() => navigate("/settings/payment-methods")}
          className="mb-4"
        >
          {t("backLink.savedCards")}
        </BackLink>

        <h1 className="text-title font-bold text-ink">{t("paymentMethods.formEditTitle")}</h1>

        <p className="mt-2 text-small text-ink-secondary">
          {t("paymentMethods.formEditSubtitle")}
        </p>

        <form
          onSubmit={handleSubmit}
          className="mt-6 rounded-card bg-paper-raised p-6 shadow-card"
        >
          <div className="mb-6 flex items-center gap-4 rounded-card border border-line bg-paper p-4">
            <div className="flex h-11 w-11 items-center justify-center rounded-control bg-paper-raised text-cedar">
              <CreditCard size={22} />
            </div>

            <div>
              <p className="font-semibold text-ink">
                •••• •••• •••• {existingLast4}
              </p>
              {existingBrand && (
                <p className="text-micro text-ink-muted">{existingBrand}</p>
              )}
            </div>
          </div>

          <div className="space-y-6">
            <p className="rounded-control bg-paper px-4 py-3 text-small text-ink-secondary">
              {t("paymentMethods.noNumberNotice")}
            </p>

            <div className="grid gap-6 sm:grid-cols-2">
              <div>
                <label
                  htmlFor="brand"
                  className="mb-2 block text-small font-medium text-ink-body"
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
                  className="w-full rounded-control border border-line-strong px-4 py-3 outline-none focus:border-cedar-ring focus:ring-2 focus:ring-cedar-tint"
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
                  className="mb-2 block text-small font-medium text-ink-body"
                >
                  {t("paymentMethods.lastFour")}
                </label>

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
                  className="w-full rounded-control border border-line-strong px-4 py-3 outline-none focus:border-cedar-ring focus:ring-2 focus:ring-cedar-tint"
                />
              </div>

              <div>
                <label
                  htmlFor="expMonth"
                  className="mb-2 block text-small font-medium text-ink-body"
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
                  className="w-full rounded-control border border-line-strong px-4 py-3 outline-none focus:border-cedar-ring focus:ring-2 focus:ring-cedar-tint"
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
                  className="mb-2 block text-small font-medium text-ink-body"
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
                  className="w-full rounded-control border border-line-strong px-4 py-3 outline-none focus:border-cedar-ring focus:ring-2 focus:ring-cedar-tint"
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
                htmlFor="cardLabel"
                className="mb-2 block text-small font-medium text-ink-body"
              >
                {t("paymentMethods.cardholderName")}
              </label>

              <input
                id="cardLabel"
                type="text"
                autoComplete="cc-name"
                value={formData.label}
                onChange={(event) =>
                  setFormData((previous) => ({
                    ...previous,
                    label: event.target.value,
                  }))
                }
                required
                className="w-full rounded-control border border-line-strong px-4 py-3 outline-none focus:border-cedar-ring focus:ring-2 focus:ring-cedar-tint"
              />
            </div>

            <label className="flex cursor-pointer items-start gap-3 rounded-control border border-line p-4">
              <input
                type="checkbox"
                checked={formData.is_default}
                onChange={(event) =>
                  setFormData((previous) => ({
                    ...previous,
                    is_default: event.target.checked,
                  }))
                }
                className="mt-1 h-4 w-4 rounded border-line-strong text-cedar focus:ring-cedar-ring"
              />

              <span>
                <span className="block text-small font-medium text-ink-emphasis">
                  {t("paymentMethods.setDefaultCard")}
                </span>
                <span className="mt-1 block text-micro text-ink-secondary">
                  Preselect this card at checkout when you do not choose Cash
                  on Delivery.
                </span>
              </span>
            </label>

            <div className="flex justify-end gap-3 border-t border-line-subtle pt-6">
              <button
                type="button"
                onClick={() => navigate("/settings/payment-methods")}
                disabled={saving}
                className="rounded-control border border-line-strong px-5 py-3 text-small font-medium text-ink-body hover:bg-paper disabled:opacity-50"
              >
                {t("paymentMethods.cancel")}
              </button>

              <button
                type="submit"
                disabled={saving}
                className="cursor-pointer rounded-control bg-cedar px-5 py-3 text-small font-semibold text-on-cedar hover:bg-cedar-strong disabled:opacity-50"
              >
                {saving ? t("common.working") : t("profile.save")}
              </button>
            </div>
          </div>
        </form>
      </div>
    </div>
  );
}

export default EditPaymentMethod;
