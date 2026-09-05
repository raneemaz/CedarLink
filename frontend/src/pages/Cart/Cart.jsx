import { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { Minus, Plus, Trash2 } from "lucide-react";
import { useTranslation } from "react-i18next";
import api from "../../services/api";
import { localizedField } from "../../utils/localize";
import CouponField from "../../components/coupon/CouponField";
import ClosedStoreNotice from "../../components/store/ClosedStoreNotice";

function Cart() {
  const { t, i18n } = useTranslation();
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
      setError(t("cart.errLoad"));
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchCart();
  }, [t]);

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
      setError(t("cart.errUpdateQty"));
    }
  };

  const removeItem = async (itemId) => {
    try {
      await api.delete(`/cart/items/${itemId}`);

      await fetchCart();
      window.dispatchEvent(new Event("cartUpdated"));
    } catch (err) {
      console.error("Failed to remove item:", err);
      setError(t("cart.errRemove"));
    }
  };

  if (loading) {
    return (
      <div className="min-h-screen bg-surface px-6 py-10">
        <div className="mx-auto max-w-7xl">
          <h1 className="text-3xl font-bold text-text-primary">
            {t("cart.title")}
          </h1>

          <p className="mt-4 text-text-secondary">
            {t("cart.loading")}
          </p>
        </div>
      </div>
    );
  }

  if (error && !cart) {
    return (
      <div className="min-h-screen bg-surface px-6 py-10">
        <div className="mx-auto max-w-7xl">
          <h1 className="text-3xl font-bold text-text-primary">
            {t("cart.title")}
          </h1>

          <p className="mt-4 text-danger">
            {error}
          </p>

          <button
            onClick={fetchCart}
            className="mt-4 rounded-lg bg-brand px-5 py-2 text-on-brand hover:bg-brand-strong"
          >
            {t("cart.tryAgain")}
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
      <div className="min-h-screen bg-surface px-6 py-10">
        <div className="mx-auto max-w-7xl">
          <h1 className="text-3xl font-bold text-text-primary">
            {t("cart.title")}
          </h1>

          <div className="mt-10 rounded-xl bg-surface-raised p-10 text-center shadow-sm">
            <h2 className="text-xl font-semibold text-text-primary">
              {t("cart.emptyTitle")}
            </h2>

            <p className="mt-2 text-text-secondary">
              {t("cart.emptyBody")}
            </p>

            <Link
              to="/products"
              className="mt-6 inline-block rounded-lg bg-brand px-6 py-3 font-medium text-on-brand transition hover:bg-brand-strong"
            >
              {t("cart.browseProducts")}
            </Link>
          </div>
        </div>
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-surface px-6 py-10">
      <div className="mx-auto max-w-7xl">

        {/* Header */}
        <div>
          <h1 className="text-3xl font-bold text-text-primary">
            {t("cart.title")}
          </h1>

          <p className="mt-2 text-text-secondary">
            {t("cart.subtitle")}
          </p>
        </div>

        {error && (
          <div className="mt-6 rounded-lg bg-danger-subtle px-4 py-3 text-danger-strong">
            {error}
          </div>
        )}

        <div className="mt-8 grid gap-8 lg:grid-cols-3">

          {/* Cart Items */}
          <div className="space-y-6 lg:col-span-2">

            {stores.map((store) => (
              <div
                key={store.store_id}
                className="overflow-hidden rounded-xl bg-surface-raised shadow-sm"
              >
                {/* Store Header */}
                <div className="border-b border-border px-6 py-4">
                  <h2 className="text-lg font-semibold text-text-primary">
                    {store.store_name ||
                      t("cart.storeHeading", { id: store.store_id })}
                  </h2>
                </div>

                {store.is_open_now === false && (
                  <div className="border-b border-border px-6 py-3">
                    <ClosedStoreNotice
                      isOpen={store.is_open_now}
                      acceptsOrders={store.accepts_orders}
                      nextOpeningTime={store.next_opening_time}
                    />
                  </div>
                )}

                {/* Store Items */}
                <div className="divide-y divide-border">
                  {store.items.map((item) => (
                    <div
                      key={item.id}
                      className="flex flex-col gap-4 px-6 py-5 sm:flex-row sm:items-center sm:justify-between"
                    >
                      {/* Product Info */}
                      <div className="flex-1">
                        <h3 className="font-semibold text-text-primary">
                          {localizedField(item, "product_name", i18n.language)}
                        </h3>

                        <p className="mt-1 text-sm text-text-muted">
                          {t("cart.priceEach", {
                            price: `$${Number(item.price).toFixed(2)}`,
                          })}
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
                          className="flex h-9 w-9 items-center justify-center rounded-lg border border-border-strong transition hover:bg-surface-sunken disabled:cursor-not-allowed disabled:opacity-40"
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
                          className="flex h-9 w-9 items-center justify-center rounded-lg border border-border-strong transition hover:bg-surface-sunken"
                        >
                          <Plus size={16} />
                        </button>
                      </div>

                      {/* Subtotal */}
                      <div className="w-24 text-end font-semibold text-text-primary">
                        ${Number(item.subtotal).toFixed(2)}
                      </div>

                      {/* Remove */}
                      <button
                        onClick={() => removeItem(item.id)}
                        className="flex h-9 w-9 items-center justify-center rounded-lg text-danger-accent transition hover:bg-danger-subtle"
                        title={t("cart.removeItem")}
                      >
                        <Trash2 size={18} />
                      </button>
                    </div>
                  ))}
                </div>

                {/* Store Subtotal */}
                <div className="flex justify-between border-t border-border bg-surface px-6 py-4">
                  <span className="font-medium text-text-body">
                    {t("cart.storeSubtotal")}
                  </span>

                  <span className="font-bold text-text-primary">
                    ${Number(store.store_subtotal).toFixed(2)}
                  </span>
                </div>
              </div>
            ))}
          </div>

          {/* Order Summary */}
          <div className="h-fit rounded-xl bg-surface-raised p-6 shadow-sm">
            <h2 className="text-xl font-semibold text-text-primary">
              {t("cart.orderSummary")}
            </h2>

            <div className="mt-6 space-y-4">
              <div className="flex justify-between text-text-secondary">
                <span>{t("cart.subtotal")}</span>

                <span dir="ltr">
                  ${Number(cart.total).toFixed(2)}
                </span>
              </div>

              {Number(cart.discount) > 0 && (
                <div className="flex justify-between text-brand">
                  <span>
                    {t("cart.discount")}{" "}
                    <span dir="ltr" className="font-mono text-xs">
                      {cart.coupon_code}
                    </span>
                  </span>

                  {/* A credit, so it is signed — and the minus sign is
                      directional, hence dir="ltr". */}
                  <span dir="ltr" className="font-medium">
                    −${Number(cart.discount).toFixed(2)}
                  </span>
                </div>
              )}

              <div className="border-t border-border pt-4">
                <CouponField
                  appliedCode={cart.coupon_code}
                  onChanged={fetchCart}
                />
              </div>

              <div className="border-t border-border pt-4">
                <div className="flex justify-between">
                  <span className="text-lg font-semibold text-text-primary">
                    {t("cart.total")}
                  </span>

                  <span dir="ltr" className="text-lg font-bold text-brand">
                    ${(
                      Number(cart.total) - Number(cart.discount || 0)
                    ).toFixed(2)}
                  </span>
                </div>
              </div>

              <Link
                to="/checkout"
                className="mt-4 block w-full rounded-lg bg-brand px-5 py-3 text-center font-medium text-on-brand transition hover:bg-brand-strong"
              >
                {t("cart.proceedToCheckout")}
              </Link>

              <Link
                to="/products"
                className="block text-center text-sm font-medium text-brand hover:underline"
              >
                {t("cart.continueShopping")}
              </Link>
            </div>
          </div>

        </div>
      </div>
    </div>
  );
}

export default Cart;