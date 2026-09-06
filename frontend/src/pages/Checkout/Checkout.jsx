import { useEffect, useState } from "react";
import { Link, useNavigate } from "react-router-dom";
import { useTranslation } from "react-i18next";
import BackLink from "../../components/common/BackLink";
import api from "../../services/api";
import CouponField from "../../components/coupon/CouponField";
import { lebanonLocations } from "../../data/lebanonLocations";
import { localizedField } from "../../utils/localize";

function Checkout() {
  const { t, i18n } = useTranslation();
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
  // Bumped by the coupon field so the preview re-runs after apply/clear.
  const [couponNonce, setCouponNonce] = useState(0);
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
            t("checkout.errLoadCart"),
        );
      } finally {
        setLoading(false);
      }
    };

    fetchCart();
  }, [t]);

  // Load saved cards, plus the user's shopping preferences and default
  // address so checkout can pre-fill. Cash on Delivery is always available.
  useEffect(() => {
    const getStoredUserId = () => {
      try {
        return JSON.parse(localStorage.getItem("user"))?.id ?? null;
      } catch {
        return null;
      }
    };

    // Return an exact district name from the checkout city <select> that
    // corresponds to `raw` (a stored city or district string).
    const matchCity = (raw) => {
      if (!raw) return "";
      const lower = String(raw).trim().toLowerCase();
      for (const location of lebanonLocations) {
        for (const district of location.districts) {
          const name = district.name.toLowerCase();
          if (
            name === lower ||
            district.cities.some((c) => c.toLowerCase() === lower)
          ) {
            return district.name;
          }
        }
      }
      return "";
    };

    const load = async () => {
      try {
        setPaymentMethodsLoading(true);
        setPaymentMethodsError("");

        const userId = getStoredUserId();

        const [methodsRes, userRes, addressesRes] = await Promise.allSettled([
          api.get("/payment-methods"),
          userId ? api.get(`/users/${userId}`) : Promise.resolve(null),
          userId ? api.get("/addresses") : Promise.resolve(null),
        ]);

        const methodsData =
          methodsRes.status === "fulfilled"
            ? methodsRes.value.data.payment_methods ||
              methodsRes.value.data ||
              []
            : [];
        const savedCards = methodsData.filter((m) => m.type === "card");
        const defaultCard =
          savedCards.find((m) => m.is_default) || savedCards[0];
        setPaymentMethods(savedCards);

        const prefs =
          userRes.status === "fulfilled" && userRes.value
            ? userRes.value.data?.user?.shopping_preferences
            : null;

        // Preferred payment method: card only if the user prefers it AND has one.
        const preferCard = prefs?.preferred_payment_method === "card";
        setSelectedPaymentMethod(
          preferCard && defaultCard
            ? String(defaultCard.id)
            : "cash_on_delivery",
        );

        const addresses =
          addressesRes.status === "fulfilled" && addressesRes.value
            ? addressesRes.value.data.addresses || []
            : [];
        const defaultAddress =
          addresses.find((a) => a.is_default) || addresses[0];

        if (prefs?.autofill_default_address && defaultAddress) {
          if (defaultAddress.address_line) {
            setDeliveryAddress((prev) => prev || defaultAddress.address_line);
          }
          const cityFromAddress = matchCity(defaultAddress.city);
          if (cityFromAddress) {
            setDeliveryCity((prev) => prev || cityFromAddress);
          }
        }

        const cityFromPref = matchCity(prefs?.default_delivery_city);
        if (cityFromPref) {
          setDeliveryCity((prev) => prev || cityFromPref);
        }
      } catch (error) {
        console.error("Failed to load checkout details:", error);
        setPaymentMethodsError(
          error.response?.data?.error ||
            error.response?.data?.message ||
            t("checkout.errMethods"),
        );
      } finally {
        setPaymentMethodsLoading(false);
      }
    };

    load();
  }, [t]);

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

        const data = error.response?.data;
        setPreviewError(
          data?.code === "store_closed"
            ? t("checkout.storeClosedError", {
                store: data.store_name || "",
              }).trim()
            : data?.error ||
                data?.message ||
                t("checkout.errCalcDelivery"),
        );
      } finally {
        setPreviewLoading(false);
      }
    };

    fetchPreview();
  }, [deliveryCity, couponNonce, t]);

  if (loading) {
    return (
      <div className="mx-auto max-w-6xl px-6 py-10">
        <p className="text-ink-secondary">{t("checkout.loading")}</p>
      </div>
    );
  }

  if (error) {
    return (
      <div className="mx-auto max-w-6xl px-6 py-10">
        <div className="rounded-card border border-danger-border bg-danger-subtle p-5">
          <p className="text-danger-strong">{error}</p>

          <BackLink to="/cart" className="mt-4">
            {t("backLink.cart")}
          </BackLink>
        </div>
      </div>
    );
  }

  const stores = cart?.stores || [];

  if (stores.length === 0) {
    return (
      <div className="mx-auto max-w-6xl px-6 py-16 text-center">
        <h1 className="text-title font-bold text-ink">
          {t("checkout.emptyTitle")}
        </h1>

        <p className="mt-3 text-ink-secondary">
          {t("checkout.emptyBody")}
        </p>

        <Link
          to="/products"
          className="mt-6 inline-block rounded-control bg-cedar px-6 py-3 font-medium text-on-cedar transition hover:bg-cedar-strong"
        >
          {t("checkout.browseProducts")}
        </Link>
      </div>
    );
  }

  const getCardLabel = (method) => {
    return method.last4
      ? `${method.label || t("checkout.cardLabelFallback")} •••• ${method.last4}`
      : method.label || t("checkout.cardLabelFallback");
  };

  const handlePlaceOrder = async () => {
    if (!deliveryAddress.trim()) {
      setOrderError(t("checkout.errEnterAddress"));
      return;
    }

    if (!deliveryCity) {
      setOrderError(t("checkout.errSelectCity"));
      return;
    }

    if (!selectedPaymentMethod) {
      setOrderError(t("checkout.errSelectPayment"));
      return;
    }

    if (!preview) {
      setOrderError(t("checkout.errWaitTotal"));
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
          t("checkout.errPlaceOrder"),
      );
    } finally {
      setPlacingOrder(false);
    }
  };

  return (
    <div className="mx-auto max-w-6xl px-6 py-10">
      <div className="mb-8">
        <BackLink to="/cart">{t("backLink.cart")}</BackLink>

        <h1 className="mt-4 text-title font-bold text-ink">
          {t("checkout.title")}
        </h1>

        <p className="mt-2 text-ink-secondary">
          {t("checkout.subtitle")}
        </p>
      </div>

      <div className="grid gap-8 lg:grid-cols-[1fr_380px]">
        <section className="space-y-6">
          {/* Delivery Information */}
          <div className="rounded-card border border-line bg-paper-raised p-6 shadow-card">
            <h2 className="text-title font-semibold text-ink">
              {t("checkout.deliveryInfo")}
            </h2>

            <div className="mt-6 space-y-5">
              <div>
                <label className="mb-2 block text-small font-medium text-ink-body">
                  {t("checkout.deliveryAddress")}
                </label>

                <input
                  type="text"
                  value={deliveryAddress}
                  onChange={(e) => setDeliveryAddress(e.target.value)}
                  placeholder={t("checkout.addressPlaceholder")}
                  className="w-full rounded-control border border-line-strong px-4 py-3 outline-none transition focus:border-cedar-ring focus:ring-2 focus:ring-cedar-tint"
                />
              </div>

              <div>
                <label className="mb-2 block text-small font-medium text-ink-body">
                  {t("checkout.city")}
                </label>

                <select
                  value={deliveryCity}
                  onChange={(e) => setDeliveryCity(e.target.value)}
                  className="w-full rounded-control border border-line-strong bg-paper-raised px-4 py-3 outline-none transition focus:border-cedar-ring focus:ring-2 focus:ring-cedar-tint"
                >
                  <option value="">{t("checkout.selectCity")}</option>

                  {lebanonLocations.flatMap((location) =>
                    location.districts.map((district) => (
                      <option
                        key={`${location.governorate}-${district.name}`}
                        value={district.name}
                      >
                        {t("checkout.cityOption", {
                          governorate: location.governorate,
                          district: district.name,
                        })}
                      </option>
                    )),
                  )}
                </select>
              </div>
            </div>
          </div>

          {/* Payment Method */}
          <div className="rounded-card border border-line bg-paper-raised p-6 shadow-card">
            <div className="flex items-center justify-between">
              <h2 className="text-title font-semibold text-ink">
                {t("checkout.paymentMethod")}
              </h2>

              <Link
                to="/settings/payment-methods"
                className="text-small font-medium text-cedar hover:underline"
              >
                {t("checkout.manageCards")}
              </Link>
            </div>

            <div className="mt-5">
              {paymentMethodsLoading && (
                <p className="text-small text-ink-muted">
                  {t("checkout.loadingMethods")}
                </p>
              )}

              {!paymentMethodsLoading && paymentMethodsError && (
                <div className="rounded-control border border-danger-border bg-danger-subtle p-4">
                  <p className="text-small text-danger-strong">
                    {paymentMethodsError}
                  </p>
                </div>
              )}

              {!paymentMethodsLoading && !paymentMethodsError && (
                <div className="space-y-3">
                  {paymentMethods.length === 0 ? (
                    <div className="rounded-control border border-warning-border bg-warning-subtle p-4">
                      <p className="text-small text-warning">
                        {t("checkout.noCardsNote")}
                      </p>

                      <Link
                        to="/settings/payment-methods/new"
                        className="mt-2 inline-block text-small font-medium text-cedar hover:underline"
                      >
                        {t("checkout.addCard")}
                      </Link>
                    </div>
                  ) : (
                    <div className="space-y-3">
                      <p className="text-small font-medium text-ink-body">
                        {t("checkout.savedCards")}
                      </p>

                      {paymentMethods.map((method) => (
                        <label
                          key={method.id}
                          className={`flex cursor-pointer items-center justify-between rounded-card border p-4 transition ${
                            selectedPaymentMethod === String(method.id)
                              ? "border-cedar-ring bg-paper-sunken"
                              : "border-line hover:border-line-strong"
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
                              <p className="font-medium text-ink">
                                {getCardLabel(method)}
                              </p>

                              {method.is_default && (
                                <p className="mt-1 text-micro text-cedar">
                                  {t("checkout.defaultCard")}
                                </p>
                              )}
                            </div>
                          </div>

                          <span className="text-small text-ink-muted">{t("checkout.card")}</span>
                        </label>
                      ))}
                    </div>
                  )}

                  <label
                    className={`flex cursor-pointer items-center justify-between rounded-card border p-4 transition ${
                      selectedPaymentMethod === "cash_on_delivery"
                        ? "border-cedar-ring bg-paper-sunken"
                        : "border-line hover:border-line-strong"
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
                        <p className="font-medium text-ink">
                          {t("checkout.cashOnDelivery")}
                        </p>
                        <p className="mt-1 text-micro text-ink-muted">
                          {t("checkout.cashOnDeliveryDesc")}
                        </p>
                      </div>
                    </div>

                    <span className="text-small text-ink-muted">{t("checkout.cash")}</span>
                  </label>
                </div>
              )}
            </div>
          </div>

          {/* Order Items */}
          <div className="rounded-card border border-line bg-paper-raised shadow-card">
            <div className="border-b border-line p-6">
              <h2 className="text-title font-semibold text-ink">
                {t("checkout.yourOrder")}
              </h2>
            </div>

            <div>
              {stores.map((store) => (
                <div
                  key={store.store_id}
                  className="border-b border-line last:border-b-0"
                >
                  <div className="bg-paper px-6 py-4">
                    <h3 className="font-semibold text-ink">
                      {store.store_name}
                    </h3>
                  </div>

                  <div className="divide-y divide-line-subtle">
                    {store.items.map((item) => (
                      <div
                        key={item.id}
                        className="flex items-center justify-between px-6 py-4"
                      >
                        <div>
                          <p className="font-medium text-ink">
                            {localizedField(item, "product_name", i18n.language)}
                          </p>

                          <p className="mt-1 text-small text-ink-muted">
                            {t("checkout.quantityLine", { count: item.quantity })}
                          </p>
                        </div>

                        <span className="font-medium text-ink">
                          {/* Server-computed line total — never multiply in
                              the client (single source of pricing truth). */}
                          ${Number(item.subtotal).toFixed(2)}
                        </span>
                      </div>
                    ))}
                  </div>

                  <div className="flex justify-between px-6 py-4">
                    <span className="font-medium text-ink-secondary">
                      {t("checkout.storeSubtotal")}
                    </span>

                    <span className="font-semibold text-ink">
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
          <div className="sticky top-24 rounded-card border border-line bg-paper-raised p-6 shadow-card">
            <h2 className="text-title font-semibold text-ink">
              {t("checkout.orderSummary")}
            </h2>

            <div className="mt-6 space-y-4">
              <div className="flex justify-between">
                <span className="text-ink-secondary">{t("checkout.cartSubtotal")}</span>

                <span className="font-medium" dir="ltr">
                  ${Number(preview?.subtotal ?? cart?.total ?? 0).toFixed(2)}
                </span>
              </div>

              <div className="flex justify-between">
                <span className="text-ink-secondary">{t("checkout.delivery")}</span>

                <span className="font-medium" dir="ltr">
                  {previewLoading
                    ? t("checkout.calculating")
                    : preview
                      ? `$${Number(preview.delivery_fee).toFixed(2)}`
                      : "—"}
                </span>
              </div>

              {Number(preview?.discount) > 0 && (
                <div className="flex justify-between text-cedar">
                  <span>
                    {t("checkout.discount")}{" "}
                    <span dir="ltr" className="font-mono text-micro">
                      {preview.coupon_code}
                    </span>
                  </span>

                  <span dir="ltr" className="font-medium">
                    −${Number(preview.discount).toFixed(2)}
                  </span>
                </div>
              )}

              {previewError && (
                <p className="text-small text-danger">{previewError}</p>
              )}

              <div className="border-t border-line pt-4">
                <CouponField
                  /* Falls back to the cart's held code so the chip does
                     not disappear between arriving here and choosing a
                     city — the coupon is applied either way. */
                  appliedCode={preview?.coupon_code ?? cart?.coupon_code}
                  disabled={previewLoading}
                  onChanged={() => setCouponNonce((n) => n + 1)}
                />
              </div>

              <div className="border-t border-line pt-4">
                <div className="flex justify-between text-body font-bold">
                  <span>{t("checkout.total")}</span>

                  <span className="text-cedar" dir="ltr">
                    ${Number(preview?.total ?? cart?.total ?? 0).toFixed(2)}
                  </span>
                </div>
              </div>

              {orderError && (
                <div className="rounded-control border border-danger-border bg-danger-subtle p-3">
                  <p className="text-small text-danger-strong">{orderError}</p>
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
                className="w-full cursor-pointer rounded-control bg-cedar px-5 py-3 font-semibold text-on-cedar transition hover:bg-cedar-strong disabled:cursor-not-allowed disabled:opacity-50"
              >
                {placingOrder ? t("checkout.placingOrder") : t("checkout.placeOrder")}
              </button>
            </div>
          </div>
        </aside>
      </div>
    </div>
  );
}

export default Checkout;
