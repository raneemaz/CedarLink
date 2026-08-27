import { useEffect, useState } from "react";
import { useNavigate } from "react-router-dom";
import { toast } from "react-toastify";
import { CreditCard } from "lucide-react";
import api from "../../services/api";

function PaymentMethods() {
  const navigate = useNavigate();

  const [paymentMethods, setPaymentMethods] = useState([]);
  const [loading, setLoading] = useState(true);

  const fetchPaymentMethods = async () => {
    try {
      const response = await api.get("/payment-methods");

      setPaymentMethods(response.data.payment_methods || []);
    } catch (error) {
      console.error("Error fetching payment methods:", error);

      const message =
        error.response?.data?.message ||
        "Failed to load your payment methods.";

      toast.error(message);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchPaymentMethods();
  }, []);

  const handleSetDefault = async (paymentMethodId) => {
    try {
      await api.patch(
        `/payment-methods/${paymentMethodId}/default`
      );

      toast.success("Default payment method updated.");

      fetchPaymentMethods();
    } catch (error) {
      console.error(
        "Error setting default payment method:",
        error
      );

      const message =
        error.response?.data?.message ||
        "Failed to update default payment method.";

      toast.error(message);
    }
  };

  const handleDelete = async (paymentMethodId) => {
    const confirmed = window.confirm(
      "Are you sure you want to delete this payment method?"
    );

    if (!confirmed) {
      return;
    }

    try {
      await api.delete(`/payment-methods/${paymentMethodId}`);

      toast.success("Payment method deleted successfully.");

      fetchPaymentMethods();
    } catch (error) {
      console.error(
        "Error deleting payment method:",
        error
      );

      const message =
        error.response?.data?.message ||
        "Failed to delete payment method.";

      toast.error(message);
    }
  };

  if (loading) {
    return (
      <div className="min-h-screen bg-gray-50 px-6 py-10">
        <div className="mx-auto max-w-4xl">
          <p className="text-gray-500">
            Loading your payment methods...
          </p>
        </div>
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-gray-50 px-6 py-10">
      <div className="mx-auto max-w-4xl">
        {/* Header */}
        <div className="mb-8">
          <button
            type="button"
            onClick={() => navigate("/settings")}
            className="mb-4 text-sm text-green-700 hover:underline"
          >
            ← Back to Settings
          </button>

          <h1 className="text-3xl font-bold text-gray-900">
            Payment Methods
          </h1>

          <p className="mt-2 text-sm text-gray-600">
            Manage the cards saved to your account.
          </p>
        </div>

        {/* Add Payment Method */}
        <div className="mb-6 flex justify-end">
          <button
            type="button"
            onClick={() =>
              navigate("/settings/payment-methods/new")
            }
            className="cursor-pointer rounded-lg bg-green-700 px-5 py-3 text-sm font-semibold text-white transition hover:bg-green-800"
          >
            + Add Card
          </button>
        </div>

        {/* Empty State */}
        {paymentMethods.length === 0 ? (
          <div className="rounded-xl bg-white p-10 text-center shadow-sm">
            <CreditCard
              size={42}
              className="mx-auto text-gray-400"
            />

            <h2 className="mt-4 text-lg font-semibold text-gray-900">
              No Saved Cards
            </h2>

            <p className="mt-2 text-sm text-gray-500">
              You don't have any saved cards yet. Cash on Delivery is
              available directly at checkout.
            </p>

            <button
              type="button"
              onClick={() =>
                navigate("/settings/payment-methods/new")
              }
              className="mt-6 cursor-pointer rounded-lg bg-green-700 px-5 py-3 text-sm font-semibold text-white hover:bg-green-800"
            >
              Add Your First Card
            </button>
          </div>
        ) : (
          /* Payment Method List */
          <div className="space-y-5">
            {paymentMethods.map((paymentMethod) => {
              return (
                <div
                  key={paymentMethod.id}
                  className="rounded-xl bg-white p-6 shadow-sm"
                >
                  {/* Top Row */}
                  <div className="flex items-start justify-between gap-4">
                    <div className="flex items-start gap-4">
                      {/* Icon */}
                      <div className="flex h-12 w-12 shrink-0 items-center justify-center rounded-xl bg-emerald-50 text-emerald-700">
                        <CreditCard size={24} />
                      </div>

                      {/* Details */}
                      <div>
                        <div className="flex flex-wrap items-center gap-3">
                          <h2 className="text-lg font-semibold text-gray-900">
                            {paymentMethod.label}
                          </h2>

                          {paymentMethod.is_default && (
                            <span className="rounded-full bg-green-100 px-3 py-1 text-xs font-semibold text-green-700">
                              Default
                            </span>
                          )}
                        </div>

                        {paymentMethod.type === "card" &&
                          paymentMethod.last4 && (
                            <p className="mt-2 text-sm text-gray-600">
                              •••• {paymentMethod.last4}
                            </p>
                          )}
                      </div>
                    </div>
                  </div>

                  {/* Actions */}
                  <div className="mt-5 flex flex-wrap items-center gap-3 border-t border-gray-100 pt-5">
                    {!paymentMethod.is_default && (
                      <button
                        type="button"
                        onClick={() =>
                          handleSetDefault(paymentMethod.id)
                        }
                        className="cursor-pointer rounded-lg border border-green-700 px-4 py-2 text-sm font-medium text-green-700 hover:bg-green-50"
                      >
                        Set as Default
                      </button>
                    )}

                    <button
                      type="button"
                      onClick={() =>
                        navigate(
                          `/settings/payment-methods/${paymentMethod.id}/edit`
                        )
                      }
                      className="cursor-pointer rounded-lg border border-gray-300 px-4 py-2 text-sm font-medium text-gray-700 hover:bg-gray-50"
                    >
                      Edit
                    </button>

                    <button
                      type="button"
                      onClick={() =>
                        handleDelete(paymentMethod.id)
                      }
                      className="cursor-pointer rounded-lg border border-red-300 px-4 py-2 text-sm font-medium text-red-600 hover:bg-red-50"
                    >
                      Delete
                    </button>
                  </div>
                </div>
              );
            })}
          </div>
        )}
      </div>
    </div>
  );
}

export default PaymentMethods;
