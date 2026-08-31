import { useCallback, useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { useTranslation } from "react-i18next";
import { toast } from "react-toastify";

import api from "../../services/api";
import Button from "../../components/common/Button/Button";
import ConfirmDialog from "../../components/common/ConfirmDialog/ConfirmDialog";
import { formatDateTime } from "../../utils/helpers";
import { localizedField } from "../../utils/localize";

const FILTERS = [
  { key: "all", labelKey: "common.all" },
  { key: "pending", labelKey: "orderStatus.pending" },
  { key: "processing", labelKey: "orderStatus.processing" },
  { key: "delivered", labelKey: "orderStatus.delivered" },
  { key: "canceled", labelKey: "orderStatus.canceled" },
];

// Mirrors the API's order state machine — never offer a rejected transition.
const ORDER_NEXT = { pending: "processing", processing: "delivered" };
const ORDER_NEXT_LABEL = {
  pending: "vendorOrders.markProcessing",
  processing: "vendorOrders.markDelivered",
};

const DELIVERY_NEXT = { assigned: "picked_up", picked_up: "delivered" };
const DELIVERY_NEXT_LABEL = {
  assigned: "vendorOrders.markPickedUp",
  picked_up: "vendorOrders.markDelivered",
};

function badgeClass(map, status) {
  return map[status] || "bg-gray-100 text-gray-700";
}

const ORDER_BADGE = {
  pending: "bg-amber-100 text-amber-700",
  processing: "bg-blue-100 text-blue-700",
  delivered: "bg-emerald-100 text-emerald-700",
  canceled: "bg-red-100 text-red-700",
};

const DELIVERY_BADGE = {
  assigned: "bg-amber-100 text-amber-700",
  picked_up: "bg-blue-100 text-blue-700",
  delivered: "bg-emerald-100 text-emerald-700",
};

function apiError(error, fallback) {
  return (
    error.response?.data?.error ||
    error.response?.data?.message ||
    fallback
  );
}

function StatusBadge({ map, status, ns }) {
  const { t } = useTranslation();
  return (
    <span
      className={`rounded-full px-2.5 py-1 text-xs font-semibold ${badgeClass(
        map,
        status,
      )}`}
    >
      {t(`${ns}.${status}`)}
    </span>
  );
}

function OrderCard({ order, onChanged }) {
  const { t, i18n } = useTranslation();
  const assignment = order.delivery_assignment;

  const [driverName, setDriverName] = useState("");
  const [driverPhone, setDriverPhone] = useState("");
  const [assigning, setAssigning] = useState(false);

  const [confirm, setConfirm] = useState(null);
  const [working, setWorking] = useState(false);

  const nextOrderStatus = ORDER_NEXT[order.status];
  const nextDeliveryStatus = assignment
    ? DELIVERY_NEXT[assignment.status]
    : null;

  const advanceOrder = async () => {
    setWorking(true);
    try {
      await api.patch(`/orders/${order.id}/status`, {
        status: nextOrderStatus,
      });
      toast.success(
        t("vendorOrders.toastOrderAdvanced", {
          id: order.id,
          status: t(`orderStatus.${nextOrderStatus}`),
        }),
      );
      setConfirm(null);
      await onChanged();
    } catch (error) {
      console.error("Failed to advance order:", error);
      toast.error(apiError(error, t("vendorOrders.errAdvanceOrder")));
    } finally {
      setWorking(false);
    }
  };

  const advanceDelivery = async () => {
    setWorking(true);
    try {
      await api.patch(
        `/delivery/assignments/${assignment.id}/status`,
        { status: nextDeliveryStatus },
      );
      toast.success(
        t("vendorOrders.toastDeliveryAdvanced", {
          status: t(`deliveryStatus.${nextDeliveryStatus}`),
        }),
      );
      setConfirm(null);
      await onChanged();
    } catch (error) {
      console.error("Failed to advance delivery:", error);
      toast.error(apiError(error, t("vendorOrders.errAdvanceDelivery")));
    } finally {
      setWorking(false);
    }
  };

  const assignDriver = async (event) => {
    event.preventDefault();

    if (!driverName.trim() || !driverPhone.trim()) {
      toast.error(t("vendorOrders.errEnterDriver"));
      return;
    }

    setAssigning(true);
    try {
      await api.post("/delivery/assignments", {
        order_id: order.id,
        driver_name: driverName.trim(),
        driver_phone: driverPhone.trim(),
      });
      toast.success(t("vendorOrders.toastDriverAssigned"));
      await onChanged();
    } catch (error) {
      console.error("Failed to assign driver:", error);
      toast.error(apiError(error, t("vendorOrders.errAssignDriver")));
    } finally {
      setAssigning(false);
    }
  };

  return (
    <div className="overflow-hidden rounded-2xl bg-white shadow-sm">
      {/* Header */}
      <div className="flex flex-wrap items-center justify-between gap-3 border-b border-gray-100 px-6 py-4">
        <div className="flex items-center gap-3">
          <h3 className="text-lg font-bold text-gray-900">
            {t("orders.orderNumber", { id: order.id })}
          </h3>
          <StatusBadge map={ORDER_BADGE} status={order.status} ns="orderStatus" />
        </div>
        <span className="text-sm text-gray-500">
          {formatDateTime(order.created_at, i18n.language)}
        </span>
      </div>

      {/* Customer + delivery target */}
      <div className="grid gap-6 border-b border-gray-100 px-6 py-5 sm:grid-cols-2">
        <div>
          <p className="mb-2 text-xs font-semibold uppercase tracking-wide text-gray-400">
            {t("vendorOrders.customer")}
          </p>
          <p className="text-gray-800">
            {order.customer.first_name} {order.customer.last_name}
          </p>
          <p className="text-sm text-gray-500">{order.customer.email}</p>
          {order.customer.phone && (
            <p className="text-sm text-gray-500">{order.customer.phone}</p>
          )}
        </div>
        <div>
          <p className="mb-2 text-xs font-semibold uppercase tracking-wide text-gray-400">
            {t("vendorOrders.deliverTo")}
          </p>
          <p className="text-gray-800">{order.delivery_address}</p>
          <p className="text-sm text-gray-500">{order.delivery_city}</p>
        </div>
      </div>

      {/* Items */}
      <div className="border-b border-gray-100 px-6 py-5">
        <p className="mb-3 text-xs font-semibold uppercase tracking-wide text-gray-400">
          {t("vendorOrders.items")}
        </p>
        <div className="space-y-2">
          {order.items.map((item) => (
            <div
              key={item.id}
              className="flex items-center justify-between text-sm"
            >
              <span className="text-gray-800">
                {localizedField(item, "product_name", i18n.language)}{" "}
                <span className="text-gray-400">x{item.quantity}</span>
              </span>
              <span className="text-gray-800">
                ${item.subtotal.toFixed(2)}
              </span>
            </div>
          ))}
        </div>
        <div className="mt-4 flex items-center justify-between border-t border-gray-100 pt-3">
          <span className="font-semibold text-gray-900">{t("orders.total")}</span>
          <span className="text-lg font-bold text-emerald-700">
            ${order.total_price.toFixed(2)}
          </span>
        </div>
      </div>

      {/* Order status action */}
      {nextOrderStatus && (
        <div className="flex justify-end border-b border-gray-100 px-6 py-4">
          <Button
            onClick={() =>
              setConfirm({
                title: t("vendorOrders.advanceOrder"),
                message: t("vendorOrders.advanceOrderConfirm", {
                  id: order.id,
                  status: t(`orderStatus.${nextOrderStatus}`),
                }),
                confirmLabel: t(ORDER_NEXT_LABEL[order.status]),
                onConfirm: advanceOrder,
              })
            }
          >
            {t(ORDER_NEXT_LABEL[order.status])}
          </Button>
        </div>
      )}

      {/* Delivery */}
      <div className="px-6 py-5">
        <p className="mb-3 text-xs font-semibold uppercase tracking-wide text-gray-400">
          {t("vendorOrders.deliverySection")}
        </p>

        {/* Both state machines, side by side — they are not coupled. */}
        <div className="mb-4 flex flex-wrap items-center gap-x-6 gap-y-2 rounded-lg bg-gray-50 px-4 py-3 text-sm">
          <span className="flex items-center gap-2 text-gray-600">
            {t("vendorOrders.orderStatusLabel")}
            <StatusBadge map={ORDER_BADGE} status={order.status} ns="orderStatus" />
          </span>
          <span className="flex items-center gap-2 text-gray-600">
            {t("vendorOrders.deliveryStatusLabel")}
            {assignment ? (
              <StatusBadge
                map={DELIVERY_BADGE}
                status={assignment.status}
                ns="deliveryStatus"
              />
            ) : (
              <span className="text-gray-400">{t("vendorOrders.noDriverAssigned")}</span>
            )}
          </span>
        </div>

        {assignment ? (
          <div className="flex flex-wrap items-center justify-between gap-4">
            <div className="text-sm">
              <p className="text-gray-800">{assignment.driver_name}</p>
              <p className="text-gray-500">{assignment.driver_phone}</p>
            </div>
            {nextDeliveryStatus && (
              <Button
                onClick={() =>
                  setConfirm({
                    title: t("vendorOrders.advanceDelivery"),
                    message: t("vendorOrders.advanceDeliveryConfirm", {
                      status: t(`deliveryStatus.${nextDeliveryStatus}`),
                    }),
                    confirmLabel: t(DELIVERY_NEXT_LABEL[assignment.status]),
                    onConfirm: advanceDelivery,
                  })
                }
              >
                {t(DELIVERY_NEXT_LABEL[assignment.status])}
              </Button>
            )}
          </div>
        ) : (
          <form
            onSubmit={assignDriver}
            className="grid gap-3 sm:grid-cols-[1fr_1fr_auto] sm:items-end"
          >
            <div>
              <label
                htmlFor={`driver-name-${order.id}`}
                className="mb-1 block text-xs font-medium text-gray-600"
              >
                {t("vendorOrders.driverName")}
              </label>
              <input
                id={`driver-name-${order.id}`}
                type="text"
                value={driverName}
                onChange={(event) => setDriverName(event.target.value)}
                className="w-full rounded-lg border border-gray-300 px-3 py-2 text-sm outline-none focus:border-green-600 focus:ring-1 focus:ring-green-600"
              />
            </div>
            <div>
              <label
                htmlFor={`driver-phone-${order.id}`}
                className="mb-1 block text-xs font-medium text-gray-600"
              >
                {t("vendorOrders.driverPhone")}
              </label>
              <input
                id={`driver-phone-${order.id}`}
                type="tel"
                value={driverPhone}
                onChange={(event) => setDriverPhone(event.target.value)}
                className="w-full rounded-lg border border-gray-300 px-3 py-2 text-sm outline-none focus:border-green-600 focus:ring-1 focus:ring-green-600"
              />
            </div>
            <Button type="submit" disabled={assigning}>
              {assigning ? t("vendorOrders.assigning") : t("vendorOrders.assignDriver")}
            </Button>
          </form>
        )}
      </div>

      <ConfirmDialog
        open={confirm !== null}
        title={confirm?.title}
        message={confirm?.message}
        confirmLabel={confirm?.confirmLabel || t("common.confirm")}
        variant="primary"
        loading={working}
        onConfirm={confirm?.onConfirm}
        onCancel={() => (working ? null : setConfirm(null))}
      />
    </div>
  );
}

function VendorOrders() {
  const { t } = useTranslation();
  const [loading, setLoading] = useState(true);
  const [noStore, setNoStore] = useState(false);
  const [orders, setOrders] = useState([]);
  const [filter, setFilter] = useState("all");
  const [refreshing, setRefreshing] = useState(false);

  const fetchOrders = useCallback(async (status) => {
    const params =
      status && status !== "all" ? { status } : undefined;
    const response = await api.get("/vendor/orders", { params });
    setOrders(response.data.orders || []);
  }, []);

  useEffect(() => {
    let cancelled = false;

    (async () => {
      try {
        await fetchOrders(filter);
      } catch (error) {
        if (cancelled) return;

        if (error.response?.status === 404) {
          setNoStore(true);
        } else {
          console.error("Failed to load orders:", error);
          toast.error(apiError(error, t("vendorOrders.errLoad")));
        }
      } finally {
        if (!cancelled) setLoading(false);
      }
    })();

    return () => {
      cancelled = true;
    };
  }, [filter, fetchOrders, t]);

  const refresh = async () => {
    setRefreshing(true);
    try {
      await fetchOrders(filter);
    } catch (error) {
      console.error("Failed to refresh orders:", error);
      toast.error(apiError(error, t("vendorOrders.errRefresh")));
    } finally {
      setRefreshing(false);
    }
  };

  if (loading) {
    return <p className="text-sm text-gray-500">{t("vendorOrders.loading")}</p>;
  }

  if (noStore) {
    return (
      <div>
        <h1 className="text-3xl font-bold text-gray-900">{t("vendorOrders.title")}</h1>
        <div className="mt-6 rounded-xl border border-dashed border-gray-300 bg-white p-12 text-center">
          <p className="text-gray-600">
            {t("vendorOrders.noStoreBody")}
          </p>
          <Link
            to="/vendor/store"
            className="mt-4 inline-block font-semibold text-emerald-700 hover:underline"
          >
            {t("vendorOrders.createStore")}
          </Link>
        </div>
      </div>
    );
  }

  return (
    <div>
      <div className="mb-6 flex items-center justify-between">
        <h1 className="text-3xl font-bold text-gray-900">{t("vendorOrders.title")}</h1>
        <button
          type="button"
          onClick={refresh}
          disabled={refreshing}
          className="text-sm font-medium text-emerald-700 hover:underline disabled:opacity-50"
        >
          {refreshing ? t("vendorOrders.refreshing") : t("vendorOrders.refresh")}
        </button>
      </div>

      <div className="mb-6 flex flex-wrap gap-2">
        {FILTERS.map(({ key, labelKey }) => (
          <button
            key={key}
            type="button"
            onClick={() => setFilter(key)}
            className={`rounded-full px-4 py-1.5 text-sm font-medium transition ${
              filter === key
                ? "bg-emerald-700 text-white"
                : "bg-white text-gray-600 shadow-sm hover:bg-gray-50"
            }`}
          >
            {t(labelKey)}
          </button>
        ))}
      </div>

      {orders.length === 0 ? (
        <div className="rounded-xl border border-dashed border-gray-300 bg-white p-12 text-center">
          <p className="text-gray-600">
            {filter === "all"
              ? t("vendorOrders.emptyAll")
              : t("vendorOrders.emptyFiltered", {
                  status: t(`orderStatus.${filter}`),
                })}
          </p>
        </div>
      ) : (
        <div className="space-y-6">
          {orders.map((order) => (
            <OrderCard
              key={order.id}
              order={order}
              onChanged={refresh}
            />
          ))}
        </div>
      )}
    </div>
  );
}

export default VendorOrders;
