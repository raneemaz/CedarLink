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
        <p className="text-slate-600">{t("orders.loading")}</p>
      </div>
    );
  }

  if (error) {
    return (
      <div className="mx-auto max-w-6xl px-6 py-10">
        <div className="rounded-xl border border-red-200 bg-red-50 p-5">
          <p className="text-red-700">{error}</p>
        </div>
      </div>
    );
  }

  if (orders.length === 0) {
    return (
      <div className="mx-auto max-w-6xl px-6 py-16 text-center">
        <h1 className="text-3xl font-bold text-slate-900">
          {t("orders.title")}
        </h1>

        <p className="mt-3 text-slate-600">
          {t("orders.emptyBody")}
        </p>

        <Link
          to="/products"
          className="mt-6 inline-block rounded-lg bg-emerald-700 px-6 py-3 font-medium text-white transition hover:bg-emerald-800"
        >
          {t("orders.browseProducts")}
        </Link>
      </div>
    );
  }

  return (
    <div className="mx-auto max-w-6xl px-6 py-10">
      <div className="mb-8">
        <h1 className="text-3xl font-bold text-slate-900">
          {t("orders.title")}
        </h1>

        <p className="mt-2 text-slate-600">
          {t("orders.subtitle")}
        </p>
      </div>

      <div className="space-y-6">
        {orders.map((order) => (
          <div
            key={order.id}
            className="rounded-2xl border border-slate-200 bg-white p-6 shadow-sm"
          >
            {/* Header */}
            <div className="flex flex-col justify-between gap-4 sm:flex-row sm:items-center">
              <div>
                <h2 className="text-lg font-semibold text-slate-900">
                  {t("orders.orderNumber", { id: order.id })}
                </h2>

                <p className="mt-1 text-sm text-slate-500">
                  {formatDate(order.created_at, i18n.language)}
                </p>
              </div>

              <span
                className={`inline-flex w-fit rounded-full px-3 py-1 text-sm font-medium ${
                  order.status === "pending"
                    ? "bg-yellow-100 text-yellow-700"
                    : order.status === "processing"
                    ? "bg-blue-100 text-blue-700"
                    : order.status === "delivered"
                    ? "bg-emerald-100 text-emerald-700"
                    : "bg-red-100 text-red-700"
                }`}
              >
                {t(`orderStatus.${order.status}`)}
              </span>
            </div>

            {/* Items */}
            <div className="mt-5 divide-y divide-slate-200 rounded-lg border border-slate-200">
              {order.items.map((item) => (
                <div
                  key={item.id}
                  className="flex items-center justify-between gap-4 p-4"
                >
                  <div>
                    <p className="font-medium text-slate-900">
                      {localizedField(item, "product_name", i18n.language)}
                    </p>

                    <p className="text-sm text-slate-500">
                      {t("orders.priceLine", {
                        price: `$${Number(item.unit_price).toFixed(2)}`,
                        quantity: item.quantity,
                      })}
                    </p>
                  </div>

                  <p className="font-semibold text-slate-900">
                    ${Number(item.subtotal).toFixed(2)}
                  </p>
                </div>
              ))}
            </div>

            {/* Footer */}
            <div className="mt-5 flex flex-col gap-4 border-t border-slate-200 pt-5 sm:flex-row sm:items-center sm:justify-between">
              <div>
                <p className="text-sm text-slate-500">
                  {t("orders.deliveryAddress")}
                </p>

                <p className="mt-1 text-sm text-slate-800">
                  {order.delivery_address}
                </p>
              </div>

              <div className="flex items-center justify-between gap-6 sm:justify-end">
                <div>
                  <p className="text-sm text-slate-500">
                    {t("orders.total")}
                  </p>

                  <p className="text-xl font-bold text-emerald-700" dir="ltr">
                    ${Number(order.total_price).toFixed(2)}
                  </p>

                  {/* The order the customer has just placed lands here, so
                      this is where they first see what came off. */}
                  {Number(order.discount) > 0 && (
                    <p className="mt-0.5 text-xs font-medium text-emerald-700">
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
                  className="rounded-lg border border-emerald-700 px-4 py-2 font-medium text-emerald-700 transition hover:bg-emerald-50"
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