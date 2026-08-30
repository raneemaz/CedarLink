import { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { Minus, Plus, Trash2 } from "lucide-react";
import api from "../../services/api";

function Cart() {
  const [cart, setCart] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");

  const fetchCart = async () => {
    try {
      setLoading(true);
      setError("");

      const response = await api.get("/cart");

      setCart(response.data);
    } catch (err) {
      console.error("Failed to fetch cart:", err);
      setError("Unable to load your cart.");
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchCart();
  }, []);

  const updateQuantity = async (itemId, newQuantity) => {
    if (newQuantity < 1) {
      return;
    }

    try {
      await api.put(`/cart/items/${itemId}`, {
        quantity: newQuantity,
      });

      await fetchCart();
      window.dispatchEvent(new Event("cartUpdated"));
    } catch (err) {
      console.error("Failed to update quantity:", err);
      setError("Unable to update the item quantity.");
    }
  };

  const removeItem = async (itemId) => {
    try {
      await api.delete(`/cart/items/${itemId}`);

      await fetchCart();
      window.dispatchEvent(new Event("cartUpdated"));
    } catch (err) {
      console.error("Failed to remove item:", err);
      setError("Unable to remove the item.");
    }
  };

  if (loading) {
    return (
      <div className="min-h-screen bg-gray-50 px-6 py-10">
        <div className="mx-auto max-w-7xl">
          <h1 className="text-3xl font-bold text-gray-900">
            Shopping Cart
          </h1>

          <p className="mt-4 text-slate-600">
            Loading your cart...
          </p>
        </div>
      </div>
    );
  }

  if (error && !cart) {
    return (
      <div className="min-h-screen bg-gray-50 px-6 py-10">
        <div className="mx-auto max-w-7xl">
          <h1 className="text-3xl font-bold text-gray-900">
            Shopping Cart
          </h1>

          <p className="mt-4 text-red-600">
            {error}
          </p>

          <button
            onClick={fetchCart}
            className="mt-4 rounded-lg bg-emerald-700 px-5 py-2 text-white hover:bg-emerald-800"
          >
            Try Again
          </button>
        </div>
      </div>
    );
  }

  const stores = cart?.stores || [];

  const isEmpty =
    stores.length === 0 ||
    stores.every((store) => store.items.length === 0);

  if (isEmpty) {
    return (
      <div className="min-h-screen bg-gray-50 px-6 py-10">
        <div className="mx-auto max-w-7xl">
          <h1 className="text-3xl font-bold text-gray-900">
            Shopping Cart
          </h1>

          <div className="mt-10 rounded-xl bg-white p-10 text-center shadow-sm">
            <h2 className="text-xl font-semibold text-gray-900">
              Your cart is empty
            </h2>

            <p className="mt-2 text-slate-600">
              Browse our products and add something to your cart.
            </p>

            <Link
              to="/products"
              className="mt-6 inline-block rounded-lg bg-emerald-700 px-6 py-3 font-medium text-white transition hover:bg-emerald-800"
            >
              Browse Products
            </Link>
          </div>
        </div>
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-gray-50 px-6 py-10">
      <div className="mx-auto max-w-7xl">

        {/* Header */}
        <div>
          <h1 className="text-3xl font-bold text-gray-900">
            Shopping Cart
          </h1>

          <p className="mt-2 text-slate-600">
            Review your selected products before checkout.
          </p>
        </div>

        {error && (
          <div className="mt-6 rounded-lg bg-red-50 px-4 py-3 text-red-700">
            {error}
          </div>
        )}

        <div className="mt-8 grid gap-8 lg:grid-cols-3">

          {/* Cart Items */}
          <div className="space-y-6 lg:col-span-2">

            {stores.map((store) => (
              <div
                key={store.store_id}
                className="overflow-hidden rounded-xl bg-white shadow-sm"
              >
                {/* Store Header */}
                <div className="border-b border-slate-200 px-6 py-4">
                  <h2 className="text-lg font-semibold text-gray-900">
                    Store #{store.store_id}
                  </h2>
                </div>

                {/* Store Items */}
                <div className="divide-y divide-slate-200">
                  {store.items.map((item) => (
                    <div
                      key={item.id}
                      className="flex flex-col gap-4 px-6 py-5 sm:flex-row sm:items-center sm:justify-between"
                    >
                      {/* Product Info */}
                      <div className="flex-1">
                        <h3 className="font-semibold text-gray-900">
                          {item.product_name}
                        </h3>

                        <p className="mt-1 text-sm text-slate-500">
                          ${Number(item.price).toFixed(2)} each
                        </p>
                      </div>

                      {/* Quantity */}
                      <div className="flex items-center gap-3">
                        <button
                          onClick={() =>
                            updateQuantity(
                              item.id,
                              item.quantity - 1
                            )
                          }
                          disabled={item.quantity <= 1}
                          className="flex h-9 w-9 items-center justify-center rounded-lg border border-slate-300 transition hover:bg-slate-100 disabled:cursor-not-allowed disabled:opacity-40"
                        >
                          <Minus size={16} />
                        </button>

                        <span className="w-8 text-center font-medium">
                          {item.quantity}
                        </span>

                        <button
                          onClick={() =>
                            updateQuantity(
                              item.id,
                              item.quantity + 1
                            )
                          }
                          className="flex h-9 w-9 items-center justify-center rounded-lg border border-slate-300 transition hover:bg-slate-100"
                        >
                          <Plus size={16} />
                        </button>
                      </div>

                      {/* Subtotal */}
                      <div className="w-24 text-end font-semibold text-gray-900">
                        ${Number(item.subtotal).toFixed(2)}
                      </div>

                      {/* Remove */}
                      <button
                        onClick={() => removeItem(item.id)}
                        className="flex h-9 w-9 items-center justify-center rounded-lg text-red-500 transition hover:bg-red-50"
                        title="Remove item"
                      >
                        <Trash2 size={18} />
                      </button>
                    </div>
                  ))}
                </div>

                {/* Store Subtotal */}
                <div className="flex justify-between border-t border-slate-200 bg-slate-50 px-6 py-4">
                  <span className="font-medium text-slate-700">
                    Store subtotal
                  </span>

                  <span className="font-bold text-gray-900">
                    ${Number(store.store_subtotal).toFixed(2)}
                  </span>
                </div>
              </div>
            ))}
          </div>

          {/* Order Summary */}
          <div className="h-fit rounded-xl bg-white p-6 shadow-sm">
            <h2 className="text-xl font-semibold text-gray-900">
              Order Summary
            </h2>

            <div className="mt-6 space-y-4">
              <div className="flex justify-between text-slate-600">
                <span>Subtotal</span>

                <span>
                  ${Number(cart.total).toFixed(2)}
                </span>
              </div>

              <div className="border-t border-slate-200 pt-4">
                <div className="flex justify-between">
                  <span className="text-lg font-semibold text-gray-900">
                    Total
                  </span>

                  <span className="text-lg font-bold text-emerald-700">
                    ${Number(cart.total).toFixed(2)}
                  </span>
                </div>
              </div>

              <Link
                to="/checkout"
                className="mt-4 block w-full rounded-lg bg-emerald-700 px-5 py-3 text-center font-medium text-white transition hover:bg-emerald-800"
              >
                Proceed to Checkout
              </Link>

              <Link
                to="/products"
                className="block text-center text-sm font-medium text-emerald-700 hover:underline"
              >
                Continue Shopping
              </Link>
            </div>
          </div>

        </div>
      </div>
    </div>
  );
}

export default Cart;