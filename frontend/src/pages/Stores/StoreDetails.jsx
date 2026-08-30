import { useEffect, useState } from "react";
import { useParams } from "react-router-dom";
import { useTranslation } from "react-i18next";
import BackLink from "../../components/common/BackLink";

import api from "../../services/api";
import ProductCard from "../../components/product/ProductCard";

function StoreDetails() {
  const { id } = useParams();
  const { t } = useTranslation();

  const [store, setStore] = useState(null);
  const [products, setProducts] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");

  useEffect(() => {
    let cancelled = false;

    const load = async () => {
      setLoading(true);
      setError("");
      try {
        const storeResponse = await api.get(`/stores/${id}`);
        if (cancelled) return;
        setStore(storeResponse.data.store);

        const productsResponse = await api.get("/products", {
          params: { store_id: id, limit: 100 },
        });
        if (cancelled) return;
        setProducts(productsResponse.data.products || []);
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

  return (
    <div className="min-h-screen bg-gray-50 px-6 py-10 lg:px-10">
      <div className="mx-auto max-w-6xl">
        <BackLink to="/stores">{t("backLink.stores")}</BackLink>

        <div className="mt-6 rounded-xl border border-gray-200 bg-white p-6">
          <h1 className="text-3xl font-bold text-gray-900">{store.name}</h1>
          <p className="mt-1 text-gray-500">
            {store.location || t("storeDetails.locationNotSet")}
          </p>

          {store.description && (
            <p className="mt-3 leading-7 text-gray-600">
              {store.description}
            </p>
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
                {store.delivery_available ? t("storeDetails.available") : t("storeDetails.unavailable")}
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
        </div>

        <h2 className="mt-10 text-xl font-bold text-gray-900">
          {t("storeDetails.productsHeading", { count: products.length })}
        </h2>

        {products.length === 0 ? (
          <p className="mt-4 text-gray-500">
            {t("storeDetails.noProducts")}
          </p>
        ) : (
          <div className="mt-4 grid gap-6 sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4">
            {products.map((product) => (
              <ProductCard key={product.id} product={product} />
            ))}
          </div>
        )}
      </div>
    </div>
  );
}

export default StoreDetails;
