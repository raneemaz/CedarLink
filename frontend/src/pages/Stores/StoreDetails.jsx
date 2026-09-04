import { useEffect, useState } from "react";
import { useParams } from "react-router-dom";
import { useTranslation } from "react-i18next";
import { Megaphone } from "lucide-react";
import BackLink from "../../components/common/BackLink";

import api from "../../services/api";
import ProductCard from "../../components/product/ProductCard";
import StoreStatusBadge from "../../components/store/StoreStatusBadge";
import ClosedStoreNotice from "../../components/store/ClosedStoreNotice";
import RatingSummary from "../../components/reviews/RatingSummary";
import ReviewList from "../../components/reviews/ReviewList";
import MapView from "../../components/map/MapView";
import { formatDateTime } from "../../utils/helpers";
import { overrideIsActive, beirutWeekday } from "../../utils/storeStatus";

const DAY_KEYS = [
  "monday",
  "tuesday",
  "wednesday",
  "thursday",
  "friday",
  "saturday",
  "sunday",
];

function StoreDetails() {
  const { id } = useParams();
  const { t, i18n } = useTranslation();

  const [store, setStore] = useState(null);
  const [products, setProducts] = useState([]);
  const [hours, setHours] = useState([]);
  const [announcements, setAnnouncements] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");

  // Captured once at mount — "now" and the Beirut weekday do not need to
  // tick while the page is open, and a lazy initializer stays render-pure.
  const [nowMs] = useState(() => Date.now());
  const [todayIdx] = useState(() => beirutWeekday());

  useEffect(() => {
    let cancelled = false;

    const load = async () => {
      setLoading(true);
      setError("");
      try {
        const storeResponse = await api.get(`/stores/${id}`);
        if (cancelled) return;
        setStore(storeResponse.data.store);

        const [productsResponse, hoursResponse, annResponse] =
          await Promise.all([
            api.get("/products", { params: { store_id: id, limit: 100 } }),
            api.get(`/stores/${id}/hours`),
            api.get(`/stores/${id}/announcements`),
          ]);
        if (cancelled) return;
        setProducts(productsResponse.data.products || []);
        setHours(hoursResponse.data.hours || []);
        setAnnouncements(annResponse.data.announcements || []);
      } catch (err) {
        if (cancelled) return;
        console.error("Failed to load store:", err);
        setError(
          err.response?.status === 404
            ? t("storeDetails.notAvailable")
            : t("storeDetails.loadError"),
        );
      } finally {
        if (!cancelled) setLoading(false);
      }
    };

    load();
    return () => {
      cancelled = true;
    };
  }, [id, t]);

  if (loading) {
    return (
      <div className="min-h-screen bg-gray-50 px-6 py-12 text-center text-gray-500">
        {t("storeDetails.loading")}
      </div>
    );
  }

  if (error) {
    return (
      <div className="min-h-screen bg-gray-50 px-6 py-12">
        <div className="mx-auto max-w-5xl">
          <BackLink to="/stores">{t("backLink.stores")}</BackLink>
          <div className="mt-8 rounded-xl bg-white p-12 text-center shadow-sm">
            <h1 className="text-xl font-semibold text-gray-900">{error}</h1>
          </div>
        </div>
      </div>
    );
  }

  const todayRanges = hours
    .filter((h) => h.day_of_week === todayIdx)
    .sort((a, b) => a.opens_at.localeCompare(b.opens_at));

  const overrideOn = overrideIsActive(store, nowMs);
  const overrideUntil = overrideOn
    ? formatDateTime(store.override_until, i18n.language)
    : null;

  return (
    <div className="min-h-screen bg-gray-50 px-6 py-10 lg:px-10">
      <div className="mx-auto max-w-6xl">
        <BackLink to="/stores">{t("backLink.stores")}</BackLink>

        <div className="mt-6 rounded-xl border border-gray-200 bg-white p-6">
          <div className="flex flex-wrap items-center gap-3">
            <h1 className="text-3xl font-bold text-gray-900">{store.name}</h1>
            <StoreStatusBadge store={store} />
          </div>
          <p className="mt-1 text-gray-500">
            {store.location || t("storeDetails.locationNotSet")}
          </p>

          <RatingSummary
            average={store.rating_avg}
            count={store.rating_count}
            className="mt-2"
          />


          {/* Only when the schedule is what shut it — an override has its
              own, more specific message just below. */}
          {!overrideOn && (
            <ClosedStoreNotice
              isOpen={store.is_open_now}
              acceptsOrders={store.accepts_orders_when_closed}
              nextOpeningTime={store.next_opening_time}
              className="mt-3"
            />
          )}

          {overrideOn && store.override_status === "closed" && (
            <p className="mt-3 rounded-lg bg-red-50 px-3 py-2 text-sm text-red-700">
              {store.override_reason
                ? t("storeDetails.overrideClosedReason", {
                    reason: store.override_reason,
                    until: overrideUntil,
                  })
                : t("storeDetails.overrideClosed", { until: overrideUntil })}
            </p>
          )}
          {overrideOn && store.override_status === "open" && (
            <p className="mt-3 rounded-lg bg-emerald-50 px-3 py-2 text-sm text-emerald-800">
              {t("storeDetails.overrideOpen", { until: overrideUntil })}
            </p>
          )}

          <div className="mt-4 text-sm">
            <p className="text-gray-400">{t("storeDetails.todaysHours")}</p>
            <p className="font-medium text-gray-800" dir="ltr">
              {todayIdx >= 0 && (
                <span className="text-gray-400">
                  {t(`storeHours.days.${DAY_KEYS[todayIdx]}`)} ·{" "}
                </span>
              )}
              {todayRanges.length === 0
                ? t("storeDetails.closedToday")
                : todayRanges
                    .map((r) => `${r.opens_at}–${r.closes_at}`)
                    .join(", ")}
            </p>
          </div>

          {store.description && (
            <p className="mt-3 leading-7 text-gray-600">{store.description}</p>
          )}

          <div className="mt-5 grid gap-4 border-t border-gray-100 pt-4 text-sm sm:grid-cols-3">
            <div>
              <p className="text-gray-400">{t("storeDetails.delivery")}</p>
              <p
                className={
                  store.delivery_available
                    ? "font-medium text-emerald-700"
                    : "font-medium text-gray-500"
                }
              >
                {store.delivery_available
                  ? t("storeDetails.available")
                  : t("storeDetails.unavailable")}
              </p>
            </div>
            <div>
              <p className="text-gray-400">{t("storeDetails.insideCityFee")}</p>
              <p className="font-medium text-gray-800">
                ${Number(store.inside_city_delivery_fee).toFixed(2)}
              </p>
            </div>
            <div>
              <p className="text-gray-400">{t("storeDetails.outsideCityFee")}</p>
              <p className="font-medium text-gray-800">
                ${Number(store.outside_city_delivery_fee).toFixed(2)}
              </p>
            </div>
          </div>

          {store.contact_info && (
            <p className="mt-4 text-sm text-gray-500">
              {t("storeDetails.contact")}: {store.contact_info}
            </p>
          )}

          {store.is_online_only ? (
            <p className="mt-4 text-sm text-gray-600">
              {t("storeDetails.onlineOnly")}
            </p>
          ) : store.latitude != null && store.longitude != null ? (
            <div className="mt-4">
              <MapView
                latitude={store.latitude}
                longitude={store.longitude}
              />
            </div>
          ) : null}
        </div>

        {announcements.length > 0 && (
          <div className="mt-6 space-y-3">
            {announcements.map((a) => (
              <div
                key={a.id}
                className="flex gap-3 rounded-xl border border-amber-200 bg-amber-50 p-4"
              >
                <Megaphone className="mt-0.5 h-5 w-5 shrink-0 text-amber-600" />
                <div>
                  <p className="font-semibold text-amber-900">{a.title}</p>
                  <p className="mt-1 text-sm text-amber-800">{a.body}</p>
                </div>
              </div>
            ))}
          </div>
        )}

        <h2 className="mt-10 text-xl font-bold text-gray-900">
          {t("storeDetails.productsHeading", { count: products.length })}
        </h2>

        {products.length === 0 ? (
          <p className="mt-4 text-gray-500">{t("storeDetails.noProducts")}</p>
        ) : (
          <div className="mt-4 grid gap-6 sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4">
            {products.map((product) => (
              <ProductCard key={product.id} product={product} />
            ))}
          </div>
        )}

        <section className="mt-10 rounded-xl border border-gray-200 bg-white p-6">
          <div className="flex flex-wrap items-center justify-between gap-3">
            <h2 className="text-xl font-bold text-gray-900">
              {t("reviews.storeHeading")}
            </h2>
            <RatingSummary
              average={store.rating_avg}
              count={store.rating_count}
            />
          </div>
          <div className="mt-5">
            <ReviewList endpoint={`/stores/${store.id}/reviews`} />
          </div>
        </section>
      </div>
    </div>
  );
}

export default StoreDetails;
