import { useEffect, useState } from "react";
import api from "../../services/api";

function VendorDashboard() {
  const [orders, setOrders] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");

  useEffect(() => {
    fetchOrders();
  }, []);

  const fetchOrders = async () => {
    try {
      setLoading(true);
      setError("");

      const response = await api.get("/vendor/orders");

      setOrders(response.data.orders || []);
    } catch (err) {
      console.error("Failed to fetch vendor orders:", err);

      setError(
        err.response?.data?.error ||
        "Failed to load orders."
      );
    } finally {
      setLoading(false);
    }
  };

  if (loading) {
    return (
      <div className="min-h-screen bg-gray-50 p-8">
        <h1 className="mb-6 text-3xl font-bold text-gray-800">
          Vendor Dashboard
        </h1>

        <p className="text-gray-600">
          Loading orders...
        </p>
      </div>
    );
  }

  if (error) {
    return (
      <div className="min-h-screen bg-gray-50 p-8">
        <h1 className="mb-6 text-3xl font-bold text-gray-800">
          Vendor Dashboard
        </h1>

        <div className="rounded-lg border border-red-200 bg-red-50 p-4 text-red-700">
          {error}
        </div>
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-gray-50 p-8">
      <div className="mx-auto max-w-6xl">

        {/* Header */}
        <div className="mb-8">
          <h1 className="text-3xl font-bold text-gray-800">
            Vendor Dashboard
          </h1>

          <p className="mt-2 text-gray-600">
            Manage your incoming orders.
          </p>
        </div>

        {/* Orders Header */}
        <div className="mb-6 flex items-center justify-between">
          <h2 className="text-2xl font-semibold text-gray-800">
            Orders
          </h2>

          <button
            onClick={fetchOrders}
            className="rounded-lg bg-green-600 px-4 py-2 font-medium text-white transition hover:bg-green-700"
          >
            Refresh
          </button>
        </div>

        {/* No Orders */}
        {orders.length === 0 ? (
          <div className="rounded-xl bg-white p-10 text-center shadow-sm">
            <p className="text-lg text-gray-600">
              No orders yet.
            </p>
          </div>
        ) : (
          <div className="space-y-6">

            {orders.map((order) => (
              <div
                key={order.id}
                className="rounded-xl bg-white p-6 shadow-sm"
              >

                {/* Order Header */}
                <div className="flex flex-col justify-between gap-4 border-b pb-4 md:flex-row md:items-center">

                  <div>
                    <h3 className="text-xl font-bold text-gray-800">
                      Order #{order.id}
                    </h3>

                    <p className="mt-1 text-sm text-gray-500">
                      {new Date(order.created_at).toLocaleString()}
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
                        : "bg-red-100 text-red-700"
                    }`}
                  >
                    {order.status.charAt(0).toUpperCase() +
                      order.status.slice(1)}
                  </span>

                </div>

                {/* Customer Information */}
                <div className="grid gap-6 border-b py-5 md:grid-cols-2">

                  <div>
                    <h4 className="mb-3 font-semibold text-gray-800">
                      Customer
                    </h4>

                    <p className="text-gray-700">
                      {order.customer.first_name}{" "}
                      {order.customer.last_name}
                    </p>

                    <p className="text-sm text-gray-500">
                      {order.customer.email}
                    </p>

                    {order.customer.phone && (
                      <p className="text-sm text-gray-500">
                        {order.customer.phone}
                      </p>
                    )}
                  </div>

                  <div>
                    <h4 className="mb-3 font-semibold text-gray-800">
                      Delivery
                    </h4>

                    <p className="text-gray-700">
                      {order.delivery_address}
                    </p>

                    {order.delivery_city && (
                      <p className="text-sm text-gray-500">
                        {order.delivery_city}
                      </p>
                    )}
                  </div>

                </div>

                {/* Products */}
                <div className="border-b py-5">

                  <h4 className="mb-4 font-semibold text-gray-800">
                    Ordered Products
                  </h4>

                  <div className="space-y-3">

                    {order.items.map((item) => (
                      <div
                        key={item.id}
                        className="flex items-center justify-between rounded-lg bg-gray-50 p-4"
                      >
                        <div>
                          <p className="font-medium text-gray-800">
                            {item.product_name}
                          </p>

                          <p className="text-sm text-gray-500">
                            Quantity: {item.quantity}
                          </p>
                        </div>

                        <p className="font-medium text-gray-800">
                          ${item.subtotal.toFixed(2)}
                        </p>
                      </div>
                    ))}

                  </div>

                </div>

                {/* Total */}
                <div className="flex items-center justify-between pt-5">

                  <span className="text-lg font-semibold text-gray-800">
                    Total
                  </span>

                  <span className="text-xl font-bold text-green-700">
                    ${order.total_price.toFixed(2)}
                  </span>

                </div>

              </div>
            ))}

          </div>
        )}

      </div>
    </div>
  );
}

export default VendorDashboard;