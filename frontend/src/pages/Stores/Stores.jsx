import { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { useTranslation } from "react-i18next";
import { toast } from "react-toastify";

import api from "../../services/api";
import { lebanonLocations } from "../../data/lebanonLocations";
import StoreStatusBadge from "../../components/store/StoreStatusBadge";
import RatingSummary from "../../components/reviews/RatingSummary";

const PAGE_SIZE = 12;

const CITY_OPTIONS = Array.from(
  new Set(
    lebanonLocations.flatMap((governorate) =>
      governorate.districts.flatMap((district) => district.cities),
    ),
  ),
).sort((a, b) => a.localeCompare(b));

function Stores() {
  const { t } = useTranslation();
  const [stores, setStores] = useState([]);
  const [page, setPage] = useState(1);
  const [pages, setPages] = useState(1);
  const [total, setTotal] = useState(0);
  const [loading, setLoading] = useState(true);

  // Draft filter inputs vs. what is actually applied to the query.
  const [keywordInput, setKeywordInput] = useState("");
  const [locationInput, setLocationInput] = useState("");
  const [applied, setApplied] = useState({ keyword: "", location: "" });

  useEffect(() => {
    let cancelled = false;

    const load = async () => {
      setLoading(true);
      try {
        const response = await api.get("/stores", {
          params: {
            keyword: applied.keyword || undefined,
            location: applied.location || undefined,
            sort: "name",
            page,
            limit: PAGE_SIZE,
          },
        });
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
  }, [applied, page, t]);

  const handleSearch = (event) => {
    event.preventDefault();
    setPage(1);
    setApplied({
      keyword: keywordInput.trim(),
      location: locationInput,
    });
  };

  return (
    <div className="min-h-screen bg-gray-50 px-2 py-2 lg:px-10">
      <div className="mx-auto max-w-screen-2xl">
        <div className="mb-8">
          <h1 className="text-2xl font-bold text-gray-900">{t("storesPage.title")}</h1>
          <p className="mt-2 text-gray-500">
            {t("storesPage.subtitle")}
          </p>
        </div>

        <form
          onSubmit={handleSearch}
          className="mb-4 rounded-xl bg-white p-2 shadow-sm"
        >
          <div className="grid gap-4 md:grid-cols-4">
            <input
              type="text"
              value={keywordInput}
              onChange={(event) => setKeywordInput(event.target.value)}
              placeholder={t("storesPage.searchPlaceholder")}
              className="rounded-md border border-gray-300 px-3 py-2 outline-none focus:border-emerald-600 md:col-span-2"
            />

            <select
              value={locationInput}
              onChange={(event) => setLocationInput(event.target.value)}
              className="rounded-md border border-gray-300 px-3 py-2 outline-none focus:border-emerald-600"
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
              className="rounded-md bg-emerald-700 px-4 py-2 font-medium text-white transition hover:bg-emerald-800"
            >
              {t("storesPage.search")}
            </button>
          </div>
        </form>

        {loading ? (
          <div className="py-20 text-center text-gray-500">
            {t("storesPage.loading")}
          </div>
        ) : stores.length === 0 ? (
          <div className="rounded-2xl bg-white py-20 text-center shadow-sm">
            <h2 className="text-xl font-semibold text-gray-800">
              {t("storesPage.noneFound")}
            </h2>
            <p className="mt-2 text-gray-500">
              {t("storesPage.tryDifferent")}
            </p>
          </div>
        ) : (
          <>
            <p className="mb-3 text-sm text-gray-500">
              {t("storesPage.count", { count: total })}
            </p>

            <div className="grid gap-6 sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4">
              {stores.map((store) => (
                <Link
                  key={store.id}
                  to={`/stores/${store.id}`}
                  className="flex flex-col rounded-xl border border-gray-200 bg-white p-5 transition duration-200 hover:-translate-y-1 hover:shadow-md"
                >
                  <div className="flex items-start justify-between gap-2">
                    <h3 className="truncate text-lg font-semibold text-gray-900">
                      {store.name}
                    </h3>
                    <StoreStatusBadge store={store} className="shrink-0" />
                  </div>
                  <p className="mt-1 text-sm text-gray-500">
                    {store.location || t("storesPage.locationNotSet")}
                  </p>

                  <RatingSummary
                    average={store.rating_avg}
                    count={store.rating_count}
                    compact
                    className="mt-1"
                  />

                  {store.description && (
                    <p className="mt-2 line-clamp-2 text-sm text-gray-500">
                      {store.description}
                    </p>
                  )}

                  <div className="mt-4 space-y-1 border-t border-gray-100 pt-3 text-sm">
                    <p
                      className={
                        store.delivery_available
                          ? "font-medium text-emerald-700"
                          : "font-medium text-gray-400"
                      }
                    >
                      {store.delivery_available
                        ? t("storesPage.deliveryAvailable")
                        : t("storesPage.deliveryUnavailable")}
                    </p>
                    <p className="text-gray-500">
                      {t("storesPage.insideCity")}: $
                      {Number(store.inside_city_delivery_fee).toFixed(2)}
                    </p>
                    <p className="text-gray-500">
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
                  className="rounded-lg border border-gray-300 px-4 py-2 font-medium text-gray-700 hover:bg-gray-50 disabled:cursor-not-allowed disabled:opacity-50"
                >
                  {t("common.previous")}
                </button>
                <span className="text-gray-500">
                  {t("common.pageOf", { page, pages })}
                </span>
                <button
                  type="button"
                  onClick={() => setPage((current) => current + 1)}
                  disabled={page >= pages}
                  className="rounded-lg border border-gray-300 px-4 py-2 font-medium text-gray-700 hover:bg-gray-50 disabled:cursor-not-allowed disabled:opacity-50"
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
