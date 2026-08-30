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
  const [formData, setFormData] = useState({
    cardNumber: "",
    label: "",
    is_default: false,
  });
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);

  const detectCardBrand = (number) => {
    const digits = number.replace(/\D/g, "");

    if (/^4/.test(digits)) return "Visa";

    if (/^(5[1-5]|2[2-7])/.test(digits)) return "Mastercard";

    return "";
  };

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
          cardNumber: "",
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

  const handleCardNumberChange = (event) => {
    let value = event.target.value.replace(/\D/g, "").slice(0, 19);
    value = value.replace(/(.{4})/g, "$1 ").trim();

    setFormData((previous) => ({
      ...previous,
      cardNumber: value,
    }));
  };

  const handleSubmit = async (event) => {
    event.preventDefault();

    const cardNumber = formData.cardNumber.replace(/\D/g, "");

    if (!formData.label.trim()) {
      toast.error(t("paymentMethods.errCardholderName"));
      return;
    }

    if (cardNumber && (cardNumber.length < 12 || cardNumber.length > 19)) {
      toast.error(t("paymentMethods.errValidNumber"));
      return;
    }

    try {
      setSaving(true);

      await api.put(`/payment-methods/${id}`, {
        type: "card",
        label: formData.label.trim(),
        ...(cardNumber ? { card_number: cardNumber } : {}),
        brand: detectCardBrand(cardNumber) || existingBrand || null,
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
      <div className="min-h-screen bg-gray-50 px-6 py-10">
        <div className="mx-auto max-w-3xl text-gray-500">
          {t("paymentMethods.formLoading")}
        </div>
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-gray-50 px-6 py-10">
      <div className="mx-auto max-w-3xl">
        <BackLink
          onClick={() => navigate("/settings/payment-methods")}
          className="mb-4"
        >
          {t("backLink.savedCards")}
        </BackLink>

        <h1 className="text-3xl font-bold text-gray-900">{t("paymentMethods.formEditTitle")}</h1>

        <p className="mt-2 text-sm text-gray-600">
          {t("paymentMethods.formEditSubtitle")}
        </p>

        <form
          onSubmit={handleSubmit}
          className="mt-6 rounded-xl bg-white p-6 shadow-sm"
        >
          <div className="mb-6 flex items-center gap-4 rounded-xl border border-gray-200 bg-gray-50 p-4">
            <div className="flex h-11 w-11 items-center justify-center rounded-lg bg-white text-green-700">
              <CreditCard size={22} />
            </div>

            <div>
              <p className="font-semibold text-gray-900">
                •••• •••• •••• {existingLast4}
              </p>
              {existingBrand && (
                <p className="text-xs text-gray-500">{existingBrand}</p>
              )}
            </div>
          </div>

          <div className="space-y-6">
            <div>
              <label
                htmlFor="cardNumber"
                className="mb-2 block text-sm font-medium text-gray-700"
              >
                {t("paymentMethods.replaceCardNumber")}
              </label>

              <input
                id="cardNumber"
                type="text"
                inputMode="numeric"
                autoComplete="cc-number"
                value={formData.cardNumber}
                onChange={handleCardNumberChange}
                placeholder={t("paymentMethods.replaceCardPlaceholder")}
                className="w-full rounded-lg border border-gray-300 px-4 py-3 outline-none focus:border-green-600 focus:ring-2 focus:ring-green-100"
              />
            </div>

            <div>
              <label
                htmlFor="cardLabel"
                className="mb-2 block text-sm font-medium text-gray-700"
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
                  Preselect this card at checkout when you do not choose Cash
                  on Delivery.
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
