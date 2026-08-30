import { useEffect, useState } from "react";
import { useParams } from "react-router-dom";
import api from "../../services/api";
import BackLink from "../../components/common/BackLink";

function OrderDetails() {
  const { id } = useParams();

  const [order, setOrder] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");

  useEffect(() => {
    const fetchOrder = async () => {
      try {
        const response = await api.get(`/orders/${id}`);

        console.log("ORDER DETAILS:", response.data.order);

        setOrder(response.data.order);
      } catch (error) {
        console.error("Failed to load order:", error);

        setError(
          error.response?.data?.error ||
            "Failed to load order details."
        );
      } finally {
        setLoading(false);
      }
    };

    fetchOrder();
  }, [id]);

  if (loading) {
    return (
      <div className="mx-auto max-w-6xl px-6 py-10">
        <p className="text-slate-600">Loading order...</p>
      </div>
    );
  }

  if (error) {
    return (
      <div className="mx-auto max-w-6xl px-6 py-10">
        <div className="rounded-xl border border-red-200 bg-red-50 p-5">
          <p className="text-red-700">{error}</p>

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

const deliveryFee = Number(order.total_price || 0) - subtotal;

const total = Number(order.total_price || 0);

  return (
    <div className="mx-auto max-w-6xl px-6 py-10">
      {/* Header */}
      <div className="mb-8">
        <BackLink to="/orders">Back to Orders</BackLink>

        <div className="mt-4 flex flex-col justify-between gap-4 sm:flex-row sm:items-center">
          <div>
            <h1 className="text-3xl font-bold text-slate-900">
              Order #{order.id}
            </h1>

            <p className="mt-2 text-slate-600">
              Review your order details.
            </p>
          </div>

          <span
            className={`w-fit rounded-full px-4 py-2 text-sm font-semibold ${
              order.status === "pending"
                ? "bg-yellow-100 text-yellow-700"
                : order.status === "processing"
                ? "bg-blue-100 text-blue-700"
                : order.status === "delivered"
                ? "bg-green-100 text-green-700"
                : order.status === "canceled"
                ? "bg-red-100 text-red-700"
                : "bg-slate-100 text-slate-700"
            }`}
          >
            {order.status}
          </span>
        </div>
      </div>

      {/* Main content */}
      <div className="grid gap-8 lg:grid-cols-3">
        {/* Order items */}
        <section className="lg:col-span-2">
          <div className="rounded-2xl border border-slate-200 bg-white shadow-sm">
            <div className="border-b border-slate-200 p-6">
              <h2 className="text-xl font-semibold text-slate-900">
                Order Items
              </h2>
            </div>

            <div className="divide-y divide-slate-200">
              {(order.items || []).map((item) => (
                <div
                  key={item.id}
                  className="flex items-center justify-between gap-4 p-6"
                >
                  <div>
                    <h3 className="font-medium text-slate-900">
                      {item.product_name}
                    </h3>

                    <p className="mt-1 text-sm text-slate-500">
                        $
                        {(Number(item.subtotal) / Number(item.quantity)).toFixed(2)} ×{" "}
                        {item.quantity}
                    </p>
                  </div>

                  <p className="font-semibold text-slate-900">
                    ${Number(item.subtotal).toFixed(2)}
                  </p>
                </div>
              ))}
            </div>
          </div>

          {/* Delivery information */}
          <div className="mt-6 rounded-2xl border border-slate-200 bg-white p-6 shadow-sm">
            <h2 className="text-xl font-semibold text-slate-900">
              Delivery Information
            </h2>

            <div className="mt-5 space-y-4">
              <div>
                <p className="text-sm text-slate-500">
                  Delivery Address
                </p>

                <p className="mt-1 font-medium text-slate-900">
                  {order.delivery_address || "Not provided"}
                </p>
              </div>

              <div>
                <p className="text-sm text-slate-500">
                  City
                </p>

                <p className="mt-1 font-medium text-slate-900">
                  {order.delivery_city || "Not provided"}
                </p>
              </div>
            </div>
          </div>
        </section>

        {/* Summary */}
<aside>
  <div className="sticky top-24 rounded-2xl border border-slate-200 bg-white p-6 shadow-sm">
    <h2 className="text-xl font-semibold text-slate-900">
      Order Summary
    </h2>

    <div className="mt-6 space-y-4">
      <div className="flex justify-between">
        <span className="text-slate-600">
          Subtotal
        </span>

        <span className="font-medium">
          ${subtotal.toFixed(2)}
        </span>
      </div>

      <div className="flex justify-between">
        <span className="text-slate-600">
          Delivery Fee
        </span>

        <span className="font-medium">
          ${deliveryFee.toFixed(2)}
        </span>
      </div>

      <div className="border-t border-slate-200 pt-4">
        <div className="flex justify-between text-lg font-bold">
          <span>Total</span>

          <span className="text-emerald-700">
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