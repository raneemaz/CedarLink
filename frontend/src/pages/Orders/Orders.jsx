import { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import api from "../../services/api";

function Orders() {
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
          error.response?.data?.error ||
            "Failed to load your orders."
        );
      } finally {
        setLoading(false);
      }
    };

    fetchOrders();
  }, []);

  if (loading) {
    return (
      <div className="mx-auto max-w-6xl px-6 py-10">
        <p className="text-slate-600">Loading your orders...</p>
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
          My Orders
        </h1>

        <p className="mt-3 text-slate-600">
          You haven't placed any orders yet.
        </p>

        <Link
          to="/products"
          className="mt-6 inline-block rounded-lg bg-emerald-700 px-6 py-3 font-medium text-white transition hover:bg-emerald-800"
        >
          Browse Products
        </Link>
      </div>
    );
  }

  return (
    <div className="mx-auto max-w-6xl px-6 py-10">
      <div className="mb-8">
        <h1 className="text-3xl font-bold text-slate-900">
          My Orders
        </h1>

        <p className="mt-2 text-slate-600">
          View and track your orders.
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
                  Order #{order.id}
                </h2>

                <p className="mt-1 text-sm text-slate-500">
                  {new Date(order.created_at).toLocaleDateString()}
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
                {order.status.charAt(0).toUpperCase() +
                  order.status.slice(1)}
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
                      {item.product_name}
                    </p>

                    <p className="text-sm text-slate-500">
                      ${Number(item.unit_price).toFixed(2)} ×{" "}
                      {item.quantity}
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
                  Delivery address
                </p>

                <p className="mt-1 text-sm text-slate-800">
                  {order.delivery_address}
                </p>
              </div>

              <div className="flex items-center justify-between gap-6 sm:justify-end">
                <div>
                  <p className="text-sm text-slate-500">
                    Total
                  </p>

                  <p className="text-xl font-bold text-emerald-700">
                    ${Number(order.total_price).toFixed(2)}
                  </p>
                </div>

                <Link
                  to={`/orders/${order.id}`}
                  className="rounded-lg border border-emerald-700 px-4 py-2 font-medium text-emerald-700 transition hover:bg-emerald-50"
                >
                  View Details
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