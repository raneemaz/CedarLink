import { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { useTranslation } from "react-i18next";
import api from "../../services/api";
import { formatDate } from "../../utils/helpers";
import { localizedField } from "../../utils/localize";

function Orders() {
  const { t, i18n } = useTranslation();
  const [orders, setOrders] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");

  useEffect(() => {
    const fetchOrders = async () => {
      try {
        const response = await api.get("/orders");

        setOrders(response.data.orders || []);
      } catch (error) {
        console.error("Failed to load orders:", error);

        setError(
          error.response?.data?.error || t("orders.errLoad")
        );
      } finally {
        setLoading(false);
      }
    };

    fetchOrders();
  }, [t]);

  if (loading) {
    return (
      <div className="mx-auto max-w-6xl px-6 py-10">
        <p className="text-ink-secondary">{t("orders.loading")}</p>
      </div>
    );
  }

  if (error) {
    return (
      <div className="mx-auto max-w-6xl px-6 py-10">
        <div className="rounded-card border border-danger-border bg-danger-subtle p-5">
          <p className="text-danger-strong">{error}</p>
        </div>
      </div>
    );
  }

  if (orders.length === 0) {
    return (
      <div className="mx-auto max-w-6xl px-6 py-16 text-center">
        <h1 className="text-title font-bold text-ink">
          {t("orders.title")}
        </h1>

        <p className="mt-3 text-ink-secondary">
          {t("orders.emptyBody")}
        </p>

        <Link
          to="/products"
          className="mt-6 inline-block rounded-control bg-cedar px-6 py-3 font-medium text-on-cedar transition hover:bg-cedar-strong"
        >
          {t("orders.browseProducts")}
        </Link>
      </div>
    );
  }

  return (
    <div className="mx-auto max-w-6xl px-6 py-10">
      <div className="mb-8">
        <h1 className="text-title font-bold text-ink">
          {t("orders.title")}
        </h1>

        <p className="mt-2 text-ink-secondary">
          {t("orders.subtitle")}
        </p>
      </div>

      <div className="space-y-6">
        {orders.map((order) => (
          <div
            key={order.id}
            className="rounded-card border border-line bg-paper-raised p-6 shadow-card"
          >
            {/* Header */}
            <div className="flex flex-col justify-between gap-4 sm:flex-row sm:items-center">
              <div>
                <h2 className="text-body font-semibold text-ink">
                  {t("orders.orderNumber", { id: order.id })}
                </h2>

                <p className="mt-1 text-small text-ink-muted">
                  {formatDate(order.created_at, i18n.language)}
                </p>
              </div>

              <span
                className={`inline-flex w-fit rounded-pill px-3 py-1 text-small font-medium ${
                  order.status === "pending"
                    ? "bg-warning-tint text-warning-muted"
                    : order.status === "processing"
                    ? "bg-info-subtle text-info"
                    : order.status === "delivered"
                    ? "bg-success-subtle text-success"
                    : "bg-danger-tint text-danger-strong"
                }`}
              >
                {t(`orderStatus.${order.status}`)}
              </span>
            </div>

            {/* Items */}
            <div className="mt-5 divide-y divide-line rounded-control border border-line">
              {order.items.map((item) => (
                <div
                  key={item.id}
                  className="flex items-center justify-between gap-4 p-4"
                >
                  <div>
                    <p className="font-medium text-ink">
                      {localizedField(item, "product_name", i18n.language)}
                    </p>

                    <p className="text-small text-ink-muted">
                      {t("orders.priceLine", {
                        price: `$${Number(item.unit_price).toFixed(2)}`,
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

            {/* Footer */}
            <div className="mt-5 flex flex-col gap-4 border-t border-line pt-5 sm:flex-row sm:items-center sm:justify-between">
              <div>
                <p className="text-small text-ink-muted">
                  {t("orders.deliveryAddress")}
                </p>

                <p className="mt-1 text-small text-ink-emphasis">
                  {order.delivery_address}
                </p>
              </div>

              <div className="flex items-center justify-between gap-6 sm:justify-end">
                <div>
                  <p className="text-small text-ink-muted">
                    {t("orders.total")}
                  </p>

                  <p className="text-title font-bold text-cedar" dir="ltr">
                    ${Number(order.total_price).toFixed(2)}
                  </p>

                  {/* The order the customer has just placed lands here, so
                      this is where they first see what came off. */}
                  {Number(order.discount) > 0 && (
                    <p className="mt-0.5 text-micro font-medium text-cedar">
                      {t("orders.discountApplied", {
                        code: order.coupon_code,
                      })}{" "}
                      <span dir="ltr">
                        −${Number(order.discount).toFixed(2)}
                      </span>
                    </p>
                  )}
                </div>

                <Link
                  to={`/orders/${order.id}`}
                  className="rounded-control border border-cedar px-4 py-2 font-medium text-cedar transition hover:bg-paper-sunken"
                >
                  {t("orders.viewDetails")}
                </Link>
              </div>
            </div>
          </div>
        ))}
      </div>
    </div>
  );
}

export default Orders;