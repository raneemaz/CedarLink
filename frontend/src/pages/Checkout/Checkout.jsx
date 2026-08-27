import { useEffect, useState } from "react";
import { Link, useNavigate } from "react-router-dom";
import api from "../../services/api";
import { lebanonLocations } from "../../data/lebanonLocations";

function Checkout() {
  const navigate = useNavigate();

  const [cart, setCart] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");

  const [paymentMethods, setPaymentMethods] = useState([]);
  const [paymentMethodsLoading, setPaymentMethodsLoading] = useState(true);
  const [paymentMethodsError, setPaymentMethodsError] = useState("");
  const [selectedPaymentMethod, setSelectedPaymentMethod] = useState("");

  const [deliveryAddress, setDeliveryAddress] = useState("");
  const [deliveryCity, setDeliveryCity] = useState("");

  const [preview, setPreview] = useState(null);
  const [previewLoading, setPreviewLoading] = useState(false);
  const [previewError, setPreviewError] = useState("");

  const [placingOrder, setPlacingOrder] = useState(false);
  const [orderError, setOrderError] = useState("");

  // Load cart
  useEffect(() => {
    const fetchCart = async () => {
      try {
        const response = await api.get("/cart");

        setCart(response.data);
      } catch (error) {
        console.error("Failed to load cart:", error);

        setError(
          error.response?.data?.error ||
            error.response?.data?.message ||
            "Failed to load your cart.",
        );
      } finally {
        setLoading(false);
      }
    };

    fetchCart();
  }, []);

  // Load saved cards separately. Cash on Delivery is always available below.
  useEffect(() => {
    const fetchPaymentMethods = async () => {
      try {
        setPaymentMethodsLoading(true);
        setPaymentMethodsError("");

        const response = await api.get("/payment-methods");

        const methods = response.data.payment_methods || response.data || [];
        const savedCards = methods.filter((method) => method.type === "card");
        const defaultCard = savedCards.find((method) => method.is_default);

        setPaymentMethods(savedCards);
        setSelectedPaymentMethod(
          defaultCard ? String(defaultCard.id) : "cash_on_delivery",
        );
      } catch (error) {
        console.error("Failed to load payment methods:", error);

        setPaymentMethodsError(
          error.response?.data?.error ||
            error.response?.data?.message ||
            "Failed to load your payment methods.",
        );
      } finally {
        setPaymentMethodsLoading(false);
      }
    };

    fetchPaymentMethods();
  }, []);

  // Calculate delivery preview
  useEffect(() => {
    if (!deliveryCity) {
      setPreview(null);
      setPreviewError("");
      return;
    }

    const fetchPreview = async () => {
      try {
        setPreviewLoading(true);
        setPreviewError("");

        const response = await api.post("/orders/preview", {
          delivery_city: deliveryCity,
        });

        setPreview(response.data);
      } catch (error) {
        console.error("Failed to calculate checkout:", error);

        setPreview(null);

        setPreviewError(
          error.response?.data?.error ||
            error.response?.data?.message ||
            "Failed to calculate delivery.",
        );
      } finally {
        setPreviewLoading(false);
      }
    };

    fetchPreview();
  }, [deliveryCity]);

  if (loading) {
    return (
      <div className="mx-auto max-w-6xl px-6 py-10">
        <p className="text-slate-600">Loading checkout...</p>
      </div>
    );
  }

  if (error) {
    return (
      <div className="mx-auto max-w-6xl px-6 py-10">
        <div className="rounded-xl border border-red-200 bg-red-50 p-5">
          <p className="text-red-700">{error}</p>

          <Link
            to="/cart"
            className="mt-4 inline-block font-medium text-emerald-700 hover:underline"
          >
            ← Back to Cart
          </Link>
        </div>
      </div>
    );
  }

  const stores = cart?.stores || [];

  if (stores.length === 0) {
    return (
      <div className="mx-auto max-w-6xl px-6 py-16 text-center">
        <h1 className="text-3xl font-bold text-slate-900">
          Your cart is empty
        </h1>

        <p className="mt-3 text-slate-600">
          Add some products before proceeding to checkout.
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

  const getCardLabel = (method) => {
    return method.last4
      ? `${method.label || "Card"} •••• ${method.last4}`
      : method.label || "Card";
  };

  const handlePlaceOrder = async () => {
    if (!deliveryAddress.trim()) {
      setOrderError("Please enter your delivery address.");
      return;
    }

    if (!deliveryCity) {
      setOrderError("Please select your city.");
      return;
    }

    if (!selectedPaymentMethod) {
      setOrderError("Please select a payment method.");
      return;
    }

    if (!preview) {
      setOrderError("Please wait for the delivery total to be calculated.");
      return;
    }

    try {
      setPlacingOrder(true);
      setOrderError("");

      const paymentSelection =
        selectedPaymentMethod === "cash_on_delivery"
          ? { payment_method: "cash_on_delivery" }
          : {
              payment_method: "card",
              payment_method_id: Number(selectedPaymentMethod),
            };

      const response = await api.post("/orders", {
        delivery_address: deliveryAddress.trim(),
        delivery_city: deliveryCity,
        ...paymentSelection,
      });

      console.log("ORDER RESPONSE:", response.data);

      navigate("/orders");
    } catch (error) {
      console.error("Failed to place order:", error);

      setOrderError(
        error.response?.data?.error ||
          error.response?.data?.message ||
          "Failed to place your order. Please try again.",
      );
    } finally {
      setPlacingOrder(false);
    }
  };

  return (
    <div className="mx-auto max-w-6xl px-6 py-10">
      <div className="mb-8">
        <Link
          to="/cart"
          className="text-sm font-medium text-emerald-700 hover:underline"
        >
          ← Back to Cart
        </Link>

        <h1 className="mt-4 text-3xl font-bold text-slate-900">
          Checkout
        </h1>

        <p className="mt-2 text-slate-600">
          Enter your delivery information and review your order.
        </p>
      </div>

      <div className="grid gap-8 lg:grid-cols-[1fr_380px]">
        <section className="space-y-6">
          {/* Delivery Information */}
          <div className="rounded-2xl border border-slate-200 bg-white p-6 shadow-sm">
            <h2 className="text-xl font-semibold text-slate-900">
              Delivery Information
            </h2>

            <div className="mt-6 space-y-5">
              <div>
                <label className="mb-2 block text-sm font-medium text-slate-700">
                  Delivery Address
                </label>

                <input
                  type="text"
                  value={deliveryAddress}
                  onChange={(e) => setDeliveryAddress(e.target.value)}
                  placeholder="Enter your full delivery address"
                  className="w-full rounded-lg border border-slate-300 px-4 py-3 outline-none transition focus:border-emerald-600 focus:ring-2 focus:ring-emerald-100"
                />
              </div>

              <div>
                <label className="mb-2 block text-sm font-medium text-slate-700">
                  City
                </label>

                <select
                  value={deliveryCity}
                  onChange={(e) => setDeliveryCity(e.target.value)}
                  className="w-full rounded-lg border border-slate-300 bg-white px-4 py-3 outline-none transition focus:border-emerald-600 focus:ring-2 focus:ring-emerald-100"
                >
                  <option value="">Select your city</option>

                  {lebanonLocations.map((location) => {
                    const locationValue = `${location.governorate}, ${location.district}`;

                    return (
                      <option
                        key={locationValue}
                        value={locationValue}
                      >
                        {location.governorate} - {location.district}
                      </option>
                    );
                  })}
                </select>
              </div>
            </div>
          </div>

          {/* Payment Method */}
          <div className="rounded-2xl border border-slate-200 bg-white p-6 shadow-sm">
            <div className="flex items-center justify-between">
              <h2 className="text-xl font-semibold text-slate-900">
                Payment Method
              </h2>

              <Link
                to="/settings/payment-methods"
                className="text-sm font-medium text-emerald-700 hover:underline"
              >
                Manage cards
              </Link>
            </div>

            <div className="mt-5">
              {paymentMethodsLoading && (
                <p className="text-sm text-slate-500">
                  Loading payment methods...
                </p>
              )}

              {!paymentMethodsLoading && paymentMethodsError && (
                <div className="rounded-lg border border-red-200 bg-red-50 p-4">
                  <p className="text-sm text-red-700">
                    {paymentMethodsError}
                  </p>
                </div>
              )}

              {!paymentMethodsLoading && !paymentMethodsError && (
                <div className="space-y-3">
                  {paymentMethods.length === 0 ? (
                    <div className="rounded-lg border border-amber-200 bg-amber-50 p-4">
                      <p className="text-sm text-amber-800">
                        You do not have any saved cards yet. You can still pay
                        with Cash on Delivery.
                      </p>

                      <Link
                        to="/settings/payment-methods/new"
                        className="mt-2 inline-block text-sm font-medium text-emerald-700 hover:underline"
                      >
                        Add a card
                      </Link>
                    </div>
                  ) : (
                    <div className="space-y-3">
                      <p className="text-sm font-medium text-slate-700">
                        Saved cards
                      </p>

                      {paymentMethods.map((method) => (
                        <label
                          key={method.id}
                          className={`flex cursor-pointer items-center justify-between rounded-xl border p-4 transition ${
                            selectedPaymentMethod === String(method.id)
                              ? "border-emerald-600 bg-emerald-50"
                              : "border-slate-200 hover:border-slate-300"
                          }`}
                        >
                          <div className="flex items-center gap-3">
                            <input
                              type="radio"
                              name="paymentMethod"
                              value={method.id}
                              checked={
                                selectedPaymentMethod === String(method.id)
                              }
                              onChange={(event) =>
                                setSelectedPaymentMethod(event.target.value)
                              }
                              className="h-4 w-4"
                            />

                            <div>
                              <p className="font-medium text-slate-900">
                                {getCardLabel(method)}
                              </p>

                              {method.is_default && (
                                <p className="mt-1 text-xs text-emerald-700">
                                  Default card
                                </p>
                              )}
                            </div>
                          </div>

                          <span className="text-sm text-slate-500">Card</span>
                        </label>
                      ))}
                    </div>
                  )}

                  <label
                    className={`flex cursor-pointer items-center justify-between rounded-xl border p-4 transition ${
                      selectedPaymentMethod === "cash_on_delivery"
                        ? "border-emerald-600 bg-emerald-50"
                        : "border-slate-200 hover:border-slate-300"
                    }`}
                  >
                    <div className="flex items-center gap-3">
                      <input
                        type="radio"
                        name="paymentMethod"
                        value="cash_on_delivery"
                        checked={selectedPaymentMethod === "cash_on_delivery"}
                        onChange={(event) =>
                          setSelectedPaymentMethod(event.target.value)
                        }
                        className="h-4 w-4"
                      />

                      <div>
                        <p className="font-medium text-slate-900">
                          Cash on Delivery
                        </p>
                        <p className="mt-1 text-xs text-slate-500">
                          Pay when your order arrives.
                        </p>
                      </div>
                    </div>

                    <span className="text-sm text-slate-500">Cash</span>
                  </label>
                </div>
              )}
            </div>
          </div>

          {/* Order Items */}
          <div className="rounded-2xl border border-slate-200 bg-white shadow-sm">
            <div className="border-b border-slate-200 p-6">
              <h2 className="text-xl font-semibold text-slate-900">
                Your Order
              </h2>
            </div>

            <div>
              {stores.map((store) => (
                <div
                  key={store.store_id}
                  className="border-b border-slate-200 last:border-b-0"
                >
                  <div className="bg-slate-50 px-6 py-4">
                    <h3 className="font-semibold text-slate-900">
                      {store.store_name}
                    </h3>
                  </div>

                  <div className="divide-y divide-slate-100">
                    {store.items.map((item) => (
                      <div
                        key={item.id}
                        className="flex items-center justify-between px-6 py-4"
                      >
                        <div>
                          <p className="font-medium text-slate-900">
                            {item.product_name}
                          </p>

                          <p className="mt-1 text-sm text-slate-500">
                            Quantity: {item.quantity}
                          </p>
                        </div>

                        <span className="font-medium text-slate-900">
                          $
                          {(Number(item.price) * Number(item.quantity)).toFixed(
                            2,
                          )}
                        </span>
                      </div>
                    ))}
                  </div>

                  <div className="flex justify-between px-6 py-4">
                    <span className="font-medium text-slate-600">
                      Store subtotal
                    </span>

                    <span className="font-semibold text-slate-900">
                      ${Number(store.store_subtotal).toFixed(2)}
                    </span>
                  </div>
                </div>
              ))}
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
                <span className="text-slate-600">Cart subtotal</span>

                <span className="font-medium">
                  ${Number(preview?.subtotal ?? cart?.total ?? 0).toFixed(2)}
                </span>
              </div>

              <div className="flex justify-between">
                <span className="text-slate-600">Delivery</span>

                <span className="font-medium">
                  {previewLoading
                    ? "Calculating..."
                    : preview
                      ? `$${Number(preview.delivery_fee).toFixed(2)}`
                      : "—"}
                </span>
              </div>

              {previewError && (
                <p className="text-sm text-red-600">{previewError}</p>
              )}

              <div className="border-t border-slate-200 pt-4">
                <div className="flex justify-between text-lg font-bold">
                  <span>Total</span>

                  <span className="text-emerald-700">
                    ${Number(preview?.total ?? cart?.total ?? 0).toFixed(2)}
                  </span>
                </div>
              </div>

              {orderError && (
                <div className="rounded-lg border border-red-200 bg-red-50 p-3">
                  <p className="text-sm text-red-700">{orderError}</p>
                </div>
              )}

              <button
                type="button"
                onClick={handlePlaceOrder}
                disabled={
                  !preview ||
                  previewLoading ||
                  placingOrder ||
                  !deliveryAddress.trim() ||
                  !deliveryCity ||
                  !selectedPaymentMethod
                }
                className="w-full cursor-pointer rounded-lg bg-emerald-700 px-5 py-3 font-semibold text-white transition hover:bg-emerald-800 disabled:cursor-not-allowed disabled:opacity-50"
              >
                {placingOrder ? "Placing Order..." : "Place Order"}
              </button>
            </div>
          </div>
        </aside>
      </div>
    </div>
  );
}

export default Checkout;
