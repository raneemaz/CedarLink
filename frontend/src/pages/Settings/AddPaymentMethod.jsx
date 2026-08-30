import { useState } from "react";
import { useNavigate } from "react-router-dom";
import { CreditCard } from "lucide-react";
import { toast } from "react-toastify";
import BackLink from "../../components/common/BackLink";

import api from "../../services/api";


function AddPaymentMethod() {
  const navigate = useNavigate();
  const [formData, setFormData] = useState({
    cardNumber: "",
    cardholderName: "",
    is_default: false,
  });
  const [saving, setSaving] = useState(false);

  const detectCardBrand = (number) => {
    const digits = number.replace(/\D/g, "");

    if (/^4/.test(digits)) return "Visa";

    if (/^(5[1-5]|2[2-7])/.test(digits)) return "Mastercard";

    return "";
  };

  const cardBrand = detectCardBrand(formData.cardNumber);

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

    if (cardNumber.length < 12 || cardNumber.length > 19) {
      toast.error("Please enter a valid card number.");
      return;
    }

    if (!formData.cardholderName.trim()) {
      toast.error("Please enter the cardholder name.");
      return;
    }

    try {
      setSaving(true);

      await api.post("/payment-methods", {
        type: "card",
        label: formData.cardholderName.trim(),
        card_number: cardNumber,
        brand: cardBrand || null,
        is_default: formData.is_default,
      });

      toast.success("Card added successfully.");
      navigate("/settings/payment-methods");
    } catch (error) {
      console.error("Error adding card:", error);
      toast.error(
        error.response?.data?.message || "Failed to add your card.",
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
          Back to Saved Cards
        </BackLink>

        <h1 className="text-3xl font-bold text-gray-900">Add Card</h1>

        <p className="mt-2 text-sm text-gray-600">
          Save a card to use during checkout. Cash on Delivery is selected
          directly at checkout and is never saved here.
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
              <p className="font-semibold text-gray-900">Card</p>
              <p className="text-xs text-gray-500">
                Credit or debit card
              </p>
            </div>
          </div>

          <div className="space-y-6">
            <div>
              <label
                htmlFor="cardNumber"
                className="mb-2 block text-sm font-medium text-gray-700"
              >
                Card Number
              </label>

              <input
                id="cardNumber"
                type="text"
                inputMode="numeric"
                autoComplete="cc-number"
                value={formData.cardNumber}
                onChange={handleCardNumberChange}
                placeholder="1234 5678 9012 3456"
                required
                className="w-full rounded-lg border border-gray-300 px-4 py-3 outline-none focus:border-green-600 focus:ring-2 focus:ring-green-100"
              />

              {cardBrand && (
                <p className="mt-2 text-sm font-medium text-green-700">
                  {cardBrand}
                </p>
              )}
            </div>

            <div>
              <label
                htmlFor="cardholderName"
                className="mb-2 block text-sm font-medium text-gray-700"
              >
                Cardholder Name
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
                placeholder="Name on card"
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
                  Set as default card
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
                Cancel
              </button>

              <button
                type="submit"
                disabled={saving}
                className="cursor-pointer rounded-lg bg-green-700 px-5 py-3 text-sm font-semibold text-white hover:bg-green-800 disabled:opacity-50"
              >
                {saving ? "Saving..." : "Save Card"}
              </button>
            </div>
          </div>
        </form>
      </div>
    </div>
  );
}

export default AddPaymentMethod;
