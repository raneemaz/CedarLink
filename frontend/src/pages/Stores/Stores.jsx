import { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { useTranslation } from "react-i18next";
import { toast } from "react-toastify";

import api from "../../services/api";
import { useAuth } from "../../context/AuthContext";
import { lebanonLocations } from "../../data/lebanonLocations";
import StoreStatusBadge from "../../components/store/StoreStatusBadge";
import RatingSummary from "../../components/reviews/RatingSummary";
import NearbySearch from "./NearbySearch";
import { formattingLocale } from "../../utils/helpers";

const PAGE_SIZE = 12;
const DEFAULT_RADIUS_KM = 5;

const CITY_OPTIONS = Array.from(
  new Set(
    lebanonLocations.flatMap((governorate) =>
      governorate.districts.flatMap((district) => district.cities),
    ),
  ),
).sort((a, b) => a.localeCompare(b));

function Stores() {
  const { t, i18n } = useTranslation();
  const { isAuthenticated } = useAuth();
  const [stores, setStores] = useState([]);
  const [page, setPage] = useState(1);
  const [pages, setPages] = useState(1);
  const [total, setTotal] = useState(0);
  const [loading, setLoading] = useState(true);

  // Draft filter inputs vs. what is actually applied to the query.
  const [keywordInput, setKeywordInput] = useState("");
  const [locationInput, setLocationInput] = useState("");
  const [applied, setApplied] = useState({ keyword: "", location: "" });

  // Nearby search. `center` holds the customer's chosen point ONLY for the
  // lifetime of this view — it goes into the query string and nowhere
  // else: no localStorage, no URL, no persisted state, no log.
  const [center, setCenter] = useState(null);
  const [radiusKm, setRadiusKm] = useState(DEFAULT_RADIUS_KM);
  const nearby = center !== null;

  // The customer's own saved addresses, offered as one-tap search centres.
  // Unlike the live geolocation above, these coordinates are already
  // stored — the customer pinned them deliberately when saving the
  // address (ADR 0018). Signed-out visitors get "near me" and the place
  // picker only; /addresses is authenticated.
  const [savedAddresses, setSavedAddresses] = useState([]);

  useEffect(() => {
    if (!isAuthenticated) {
      setSavedAddresses([]);
      return;
    }

    let cancelled = false;

    api
      .get("/addresses")
      .then((response) => {
        if (!cancelled) {
          setSavedAddresses(response.data.addresses || []);
        }
      })
      .catch(() => {
        // A shortcut that fails to load is not worth interrupting the
        // store listing for — the other two centres still work.
        if (!cancelled) setSavedAddresses([]);
      });

    return () => {
      cancelled = true;
    };
  }, [isAuthenticated]);

  useEffect(() => {
    let cancelled = false;

    const load = async () => {
      setLoading(true);
      try {
        const params = {
          keyword: applied.keyword || undefined,
          location: applied.location || undefined,
          page,
          limit: PAGE_SIZE,
        };
        if (center) {
          params.near = `${center.lat},${center.lng}`;
          params.radius = radiusKm;
          params.sort = "distance";
        } else {
          params.sort = "name";
        }

        const response = await api.get("/stores", { params });
        if (cancelled) return;

        setStores(response.data.stores || []);
        setPages(response.data.pages || 1);
        setTotal(response.data.total || 0);
      } catch (error) {
        if (cancelled) return;
        console.error("Failed to load stores:", error);
        toast.error(
          error.response?.data?.message || t("storesPage.errLoad"),
        );
      } finally {
        if (!cancelled) setLoading(false);
      }
    };

    load();
    return () => {
      cancelled = true;
    };
  }, [applied, page, center, radiusKm, t]);

  const setSearchCenter = (next) => {
    setPage(1);
    setCenter(next);
  };

  const changeRadius = (km) => {
    setPage(1);
    setRadiusKm(km);
  };

  const distanceLabel = (km) =>
    t("storesPage.distanceAway", {
      count: km,
      km: new Intl.NumberFormat(formattingLocale(i18n.language), {
        maximumFractionDigits: 1,
      }).format(km),
    });

  const handleSearch = (event) => {
    event.preventDefault();
    setPage(1);
    setApplied({
      keyword: keywordInput.trim(),
      location: locationInput,
    });
  };

  return (
    <div className="min-h-screen bg-paper px-2 py-2 lg:px-10">
      <div className="mx-auto max-w-screen-2xl">
        <div className="mb-8">
          <h1 className="text-2xl font-bold text-ink">{t("storesPage.title")}</h1>
          <p className="mt-2 text-ink-muted">
            {t("storesPage.subtitle")}
          </p>
        </div>

        <NearbySearch
          center={center}
          radiusKm={radiusKm}
          onCenterChange={setSearchCenter}
          onRadiusChange={changeRadius}
          savedAddresses={savedAddresses}
        />

        <form
          onSubmit={handleSearch}
          className="mb-4 rounded-xl bg-paper-raised p-2 shadow-sm"
        >
          <div className="grid gap-4 md:grid-cols-4">
            <input
              type="text"
              value={keywordInput}
              onChange={(event) => setKeywordInput(event.target.value)}
              placeholder={t("storesPage.searchPlaceholder")}
              className="rounded-md border border-line-strong px-3 py-2 outline-none focus:border-cedar-ring md:col-span-2"
            />

            <select
              value={locationInput}
              onChange={(event) => setLocationInput(event.target.value)}
              className="rounded-md border border-line-strong px-3 py-2 outline-none focus:border-cedar-ring"
            >
              <option value="">{t("storesPage.allLocations")}</option>
              {CITY_OPTIONS.map((city) => (
                <option key={city} value={city}>
                  {city}
                </option>
              ))}
            </select>

            <button
              type="submit"
              className="rounded-md bg-cedar px-4 py-2 font-medium text-on-cedar transition hover:bg-cedar-strong"
            >
              {t("storesPage.search")}
            </button>
          </div>
        </form>

        {loading ? (
          <div className="py-20 text-center text-ink-muted">
            {t("storesPage.loading")}
          </div>
        ) : stores.length === 0 ? (
          <div className="rounded-2xl bg-paper-raised py-20 text-center shadow-sm">
            <h2 className="text-xl font-semibold text-ink-emphasis">
              {t("storesPage.noneFound")}
            </h2>
            <p className="mt-2 text-ink-muted">
              {t("storesPage.tryDifferent")}
            </p>
          </div>
        ) : (
          <>
            <p className="mb-3 text-sm text-ink-muted">
              {nearby
                ? t("storesPage.countNearby", { count: total, km: radiusKm })
                : t("storesPage.count", { count: total })}
            </p>

            <div className="grid gap-6 sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4">
              {stores.map((store) => (
                <Link
                  key={store.id}
                  to={`/stores/${store.id}`}
                  className="flex flex-col rounded-xl border border-line bg-paper-raised p-5 transition duration-200 hover:-translate-y-1 hover:shadow-md"
                >
                  <div className="flex items-start justify-between gap-2">
                    <h3 className="truncate text-lg font-semibold text-ink">
                      {store.name}
                    </h3>
                    <StoreStatusBadge store={store} className="shrink-0" />
                  </div>
                  <div className="mt-1 flex flex-wrap items-center gap-x-2 gap-y-1 text-sm text-ink-muted">
                    <span>{store.location || t("storesPage.locationNotSet")}</span>
                    {store.is_online_only && (
                      <span className="rounded-full bg-info-subtle px-2 py-0.5 text-xs font-medium text-info">
                        {t("storesPage.onlineMarker")}
                      </span>
                    )}
                    {typeof store.distance_km === "number" && (
                      <span className="font-medium text-cedar">
                        · {distanceLabel(store.distance_km)}
                      </span>
                    )}
                  </div>

                  <RatingSummary
                    average={store.rating_avg}
                    count={store.rating_count}
                    compact
                    className="mt-1"
                  />

                  {store.description && (
                    <p className="mt-2 line-clamp-2 text-sm text-ink-muted">
                      {store.description}
                    </p>
                  )}

                  <div className="mt-4 space-y-1 border-t border-line-subtle pt-3 text-sm">
                    <p
                      className={
                        store.delivery_available
                          ? "font-medium text-cedar"
                          : "font-medium text-ink-faint"
                      }
                    >
                      {store.delivery_available
                        ? t("storesPage.deliveryAvailable")
                        : t("storesPage.deliveryUnavailable")}
                    </p>
                    <p className="text-ink-muted">
                      {t("storesPage.insideCity")}: $
                      {Number(store.inside_city_delivery_fee).toFixed(2)}
                    </p>
                    <p className="text-ink-muted">
                      {t("storesPage.outsideCity")}: $
                      {Number(store.outside_city_delivery_fee).toFixed(2)}
                    </p>
                  </div>
                </Link>
              ))}
            </div>

            {pages > 1 && (
              <div className="mt-6 flex items-center justify-between text-sm">
                <button
                  type="button"
                  onClick={() => setPage((current) => current - 1)}
                  disabled={page <= 1}
                  className="rounded-lg border border-line-strong px-4 py-2 font-medium text-ink-body hover:bg-paper disabled:cursor-not-allowed disabled:opacity-50"
                >
                  {t("common.previous")}
                </button>
                <span className="text-ink-muted">
                  {t("common.pageOf", { page, pages })}
                </span>
                <button
                  type="button"
                  onClick={() => setPage((current) => current + 1)}
                  disabled={page >= pages}
                  className="rounded-lg border border-line-strong px-4 py-2 font-medium text-ink-body hover:bg-paper disabled:cursor-not-allowed disabled:opacity-50"
                >
                  {t("common.next")}
                </button>
              </div>
            )}
          </>
        )}
      </div>
    </div>
  );
}

export default Stores;
