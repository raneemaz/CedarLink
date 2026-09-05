import { useEffect, useState } from "react";
import { useNavigate } from "react-router-dom";
import { useTranslation } from "react-i18next";
import { toast } from "react-toastify";
import { CreditCard } from "lucide-react";
import BackLink from "../../components/common/BackLink";
import api from "../../services/api";

function PaymentMethods() {
  const { t } = useTranslation();
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
        t("paymentMethods.errLoad");

      toast.error(message);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchPaymentMethods();
  }, [t]);

  const handleSetDefault = async (paymentMethodId) => {
    try {
      await api.patch(
        `/payment-methods/${paymentMethodId}/default`
      );

      toast.success(t("paymentMethods.toastDefault"));

      fetchPaymentMethods();
    } catch (error) {
      console.error(
        "Error setting default payment method:",
        error
      );

      const message =
        error.response?.data?.message ||
        t("paymentMethods.errDefault");

      toast.error(message);
    }
  };

  const handleDelete = async (paymentMethodId) => {
    const confirmed = window.confirm(t("paymentMethods.deleteConfirm"));

    if (!confirmed) {
      return;
    }

    try {
      await api.delete(`/payment-methods/${paymentMethodId}`);

      toast.success(t("paymentMethods.toastDeleted"));

      fetchPaymentMethods();
    } catch (error) {
      console.error(
        "Error deleting payment method:",
        error
      );

      const message =
        error.response?.data?.message ||
        t("paymentMethods.errDelete");

      toast.error(message);
    }
  };

  if (loading) {
    return (
      <div className="min-h-screen bg-surface px-6 py-10">
        <div className="mx-auto max-w-4xl">
          <p className="text-text-muted">
            {t("paymentMethods.loading")}
          </p>
        </div>
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-surface px-6 py-10">
      <div className="mx-auto max-w-4xl">
        {/* Header */}
        <div className="mb-8">
          <BackLink onClick={() => navigate("/settings")} className="mb-4">
            {t("backLink.settings")}
          </BackLink>

          <h1 className="text-3xl font-bold text-text-primary">
            {t("paymentMethods.title")}
          </h1>

          <p className="mt-2 text-sm text-text-secondary">
            {t("paymentMethods.subtitle")}
          </p>
        </div>

        {/* Add Payment Method */}
        <div className="mb-6 flex justify-end">
          <button
            type="button"
            onClick={() =>
              navigate("/settings/payment-methods/new")
            }
            className="cursor-pointer rounded-lg bg-brand px-5 py-3 text-sm font-semibold text-on-brand transition hover:bg-brand-strong"
          >
            + {t("paymentMethods.addCard")}
          </button>
        </div>

        {/* Empty State */}
        {paymentMethods.length === 0 ? (
          <div className="rounded-xl bg-surface-raised p-10 text-center shadow-sm">
            <CreditCard
              size={42}
              className="mx-auto text-text-faint"
            />

            <h2 className="mt-4 text-lg font-semibold text-text-primary">
              {t("paymentMethods.emptyTitle")}
            </h2>

            <p className="mt-2 text-sm text-text-muted">
              {t("paymentMethods.emptyBody")}
            </p>

            <button
              type="button"
              onClick={() =>
                navigate("/settings/payment-methods/new")
              }
              className="mt-6 cursor-pointer rounded-lg bg-brand px-5 py-3 text-sm font-semibold text-on-brand hover:bg-brand-strong"
            >
              {t("paymentMethods.addFirst")}
            </button>
          </div>
        ) : (
          /* Payment Method List */
          <div className="space-y-5">
            {paymentMethods.map((paymentMethod) => {
              return (
                <div
                  key={paymentMethod.id}
                  className="rounded-xl bg-surface-raised p-6 shadow-sm"
                >
                  {/* Top Row */}
                  <div className="flex items-start justify-between gap-4">
                    <div className="flex items-start gap-4">
                      {/* Icon */}
                      <div className="flex h-12 w-12 shrink-0 items-center justify-center rounded-xl bg-brand-subtle text-brand">
                        <CreditCard size={24} />
                      </div>

                      {/* Details */}
                      <div>
                        <div className="flex flex-wrap items-center gap-3">
                          <h2 className="text-lg font-semibold text-text-primary">
                            {paymentMethod.label}
                          </h2>

                          {paymentMethod.is_default && (
                            <span className="rounded-full bg-brand-tint px-3 py-1 text-xs font-semibold text-brand">
                              {t("common.default")}
                            </span>
                          )}
                        </div>

                        {paymentMethod.type === "card" &&
                          paymentMethod.last4 && (
                            <p className="mt-2 text-sm text-text-secondary">
                              •••• {paymentMethod.last4}
                            </p>
                          )}
                      </div>
                    </div>
                  </div>

                  {/* Actions */}
                  <div className="mt-5 flex flex-wrap items-center gap-3 border-t border-border-subtle pt-5">
                    {!paymentMethod.is_default && (
                      <button
                        type="button"
                        onClick={() =>
                          handleSetDefault(paymentMethod.id)
                        }
                        className="cursor-pointer rounded-lg border border-brand px-4 py-2 text-sm font-medium text-brand hover:bg-brand-subtle"
                      >
                        {t("paymentMethods.setAsDefault")}
                      </button>
                    )}

                    <button
                      type="button"
                      onClick={() =>
                        navigate(
                          `/settings/payment-methods/${paymentMethod.id}/edit`
                        )
                      }
                      className="cursor-pointer rounded-lg border border-border-strong px-4 py-2 text-sm font-medium text-text-body hover:bg-surface"
                    >
                      {t("paymentMethods.edit")}
                    </button>

                    <button
                      type="button"
                      onClick={() =>
                        handleDelete(paymentMethod.id)
                      }
                      className="cursor-pointer rounded-lg border border-danger-border px-4 py-2 text-sm font-medium text-danger hover:bg-danger-subtle"
                    >
                      {t("paymentMethods.delete")}
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
