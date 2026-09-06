import { useEffect, useState } from "react";
import { useParams } from "react-router-dom";
import { useTranslation } from "react-i18next";
import api from "../../services/api";
import BackLink from "../../components/common/BackLink";
import { localizedField } from "../../utils/localize";
import { useAuth } from "../../context/AuthContext";
import RateYourOrder from "../../components/reviews/RateYourOrder";

function OrderDetails() {
  const { t, i18n } = useTranslation();
  const { id } = useParams();
  const { user } = useAuth();

  const [order, setOrder] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");

  useEffect(() => {
    const fetchOrder = async () => {
      try {
        const response = await api.get(`/orders/${id}`);

        setOrder(response.data.order);
      } catch (error) {
        console.error("Failed to load order:", error);

        setError(
          error.response?.data?.error || t("orderDetails.loadError")
        );
      } finally {
        setLoading(false);
      }
    };

    fetchOrder();
  }, [id, t]);

  if (loading) {
    return (
      <div className="mx-auto max-w-6xl px-6 py-10">
        <p className="text-ink-secondary">{t("orderDetails.loading")}</p>
      </div>
    );
  }

  if (error) {
    return (
      <div className="mx-auto max-w-6xl px-6 py-10">
        <div className="rounded-card border border-danger-border bg-danger-subtle p-5">
          <p className="text-danger-strong">{error}</p>

          <BackLink to="/orders" className="mt-4">
            Back to Orders
          </BackLink>
        </div>
      </div>
    );
  }

  if (!order) {
    return null;
  }
  const subtotal = (order.items || []).reduce(
  (sum, item) => sum + Number(item.subtotal || 0),
  0
);

const discount = Number(order.discount || 0);

// Read, not derived. Recovering the fee by subtracting the goods from the
// total was only correct while nothing else was in that sum, and it broke
// the moment discounts existed. The server charges it, so the server
// records it.
const deliveryFee = Number(order.delivery_fee || 0);

const total = Number(order.total_price || 0);

  return (
    <div className="mx-auto max-w-6xl px-6 py-10">
      {/* Header */}
      <div className="mb-8">
        <BackLink to="/orders">{t("backLink.orders")}</BackLink>

        <div className="mt-4 flex flex-col justify-between gap-4 sm:flex-row sm:items-center">
          <div>
            <h1 className="text-title font-bold text-ink">
              {t("orderDetails.orderNumber", { id: order.id })}
            </h1>

            <p className="mt-2 text-ink-secondary">
              {t("orderDetails.subtitle")}
            </p>
          </div>

          <span
            className={`w-fit rounded-pill px-4 py-2 text-small font-semibold ${
              order.status === "pending"
                ? "bg-warning-tint text-warning-muted"
                : order.status === "processing"
                ? "bg-info-subtle text-info"
                : order.status === "delivered"
                ? "bg-success-subtle text-success"
                : order.status === "canceled"
                ? "bg-danger-tint text-danger-strong"
                : "bg-paper-sunken text-ink-body"
            }`}
          >
            {t(`orderStatus.${order.status}`)}
          </span>
        </div>
      </div>

      {/* Main content */}
      <div className="grid gap-8 lg:grid-cols-3">
        {/* Order items */}
        <section className="lg:col-span-2">
          <div className="rounded-card border border-line bg-paper-raised shadow-card">
            <div className="border-b border-line p-6">
              <h2 className="text-title font-semibold text-ink">
                {t("orderDetails.orderItems")}
              </h2>
            </div>

            <div className="divide-y divide-line">
              {(order.items || []).map((item) => (
                <div
                  key={item.id}
                  className="flex items-center justify-between gap-4 p-6"
                >
                  <div>
                    <h3 className="font-medium text-ink">
                      {localizedField(item, "product_name", i18n.language)}
                    </h3>

                    <p className="mt-1 text-small text-ink-muted">
                      {t("orderDetails.priceLine", {
                        price: `$${(Number(item.subtotal) / Number(item.quantity)).toFixed(2)}`,
                        quantity: item.quantity,
                      })}
                    </p>
                  </div>

                  <p className="font-semibold text-ink">
                    ${Number(item.subtotal).toFixed(2)}
                  </p>
                </div>
              ))}
            </div>
          </div>

          {/* Delivery information */}
          <div className="mt-6 rounded-card border border-line bg-paper-raised p-6 shadow-card">
            <h2 className="text-title font-semibold text-ink">
              {t("orderDetails.deliveryInfo")}
            </h2>

            <div className="mt-5 space-y-4">
              <div>
                <p className="text-small text-ink-muted">
                  {t("orderDetails.deliveryAddress")}
                </p>

                <p className="mt-1 font-medium text-ink">
                  {order.delivery_address || t("orderDetails.notProvided")}
                </p>
              </div>

              <div>
                <p className="text-small text-ink-muted">
                  {t("orderDetails.city")}
                </p>

                <p className="mt-1 font-medium text-ink">
                  {order.delivery_city || t("orderDetails.notProvided")}
                </p>
              </div>
            </div>
          </div>

          {user?.role === "customer" && order.status === "delivered" && (
            <div className="mt-6">
              <RateYourOrder orderId={order.id} />
            </div>
          )}
        </section>

        {/* Summary */}
<aside>
  <div className="sticky top-24 rounded-card border border-line bg-paper-raised p-6 shadow-card">
    <h2 className="text-title font-semibold text-ink">
      {t("orderDetails.orderSummary")}
    </h2>

    <div className="mt-6 space-y-4">
      <div className="flex justify-between">
        <span className="text-ink-secondary">
          {t("orderDetails.subtotal")}
        </span>

        <span className="font-medium" dir="ltr">
          ${subtotal.toFixed(2)}
        </span>
      </div>

      <div className="flex justify-between">
        <span className="text-ink-secondary">
          {t("orderDetails.deliveryFee")}
        </span>

        <span className="font-medium" dir="ltr">
          ${deliveryFee.toFixed(2)}
        </span>
      </div>

      {discount > 0 && (
        <div className="flex justify-between text-cedar">
          <span>
            {t("orderDetails.discount")}{" "}
            <span dir="ltr" className="font-mono text-micro">
              {order.coupon_code}
            </span>
          </span>

          <span dir="ltr" className="font-medium">
            −${discount.toFixed(2)}
          </span>
        </div>
      )}

      <div className="border-t border-line pt-4">
        <div className="flex justify-between text-body font-bold">
          <span>{t("orderDetails.total")}</span>

          <span className="text-cedar" dir="ltr">
            ${total.toFixed(2)}
          </span>
        </div>
      </div>
    </div>
  </div>
</aside>
      </div>
    </div>
  );
}

export default OrderDetails;