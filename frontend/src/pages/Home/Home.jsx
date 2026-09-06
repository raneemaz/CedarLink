import { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { useTranslation } from "react-i18next";
import { SlidersHorizontal } from "lucide-react";

import api from "../../services/api";
import ProductCard from "../../components/product/ProductCard";
import { useAuth } from "../../context/AuthContext";
import { localizedField } from "../../utils/localize";

export default function Home() {
  const { t, i18n } = useTranslation();
  const { isAuthenticated } = useAuth();

  const [sections, setSections] = useState([]);
  const [personalized, setPersonalized] = useState(false);
  const [loading, setLoading] = useState(true);
  // The mockup's hero reads "120+ local stores". The seed produces eight.
  // A fabricated figure on the home page is the first image in the
  // report, so this is the real total from the stores endpoint and the
  // stat renders only once it has one.
  const [storeCount, setStoreCount] = useState(null);

  // One request for the whole page. The order is decided on the server —
  // stated interests first, then the busiest categories — so a signed-out
  // visitor and a customer with five interests take the same path here.
  useEffect(() => {
    let cancelled = false;

    (async () => {
      try {
        const response = await api.get("/home/sections");

        if (cancelled) return;

        setSections(response.data.sections || []);
        setPersonalized(Boolean(response.data.personalized));

        // Cheapest possible ask: one row, for the pagination total.
        const stores = await api.get("/stores", {
          params: { per_page: 1 },
        });
        if (!cancelled) {
          setStoreCount(stores.data?.total ?? null);
        }
      } catch (error) {
        console.error("Failed to load home sections:", error);
      } finally {
        if (!cancelled) setLoading(false);
      }
    })();

    return () => {
      cancelled = true;
    };
  }, []);

  return (
    <div className="space-y-12">
      {/* Hero */}
      <section className="grid gap-8 rounded-card bg-gradient-to-r from-cedar to-cedar-ring px-6 py-12 text-on-cedar md:grid-cols-2 md:px-10">
        <div className="space-y-5">
          <span className="inline-flex rounded-pill bg-on-cedar/15 px-4 py-1 text-small font-medium">
            {t("home.hero.badge")}
          </span>

          <h1 className="text-display font-bold leading-tight md:text-display">
            {t("home.hero.title")}
          </h1>

          <p className="max-w-xl text-on-cedar/90">
            {t("home.hero.description")}
          </p>

          {storeCount !== null && (
            <p className="text-small text-on-cedar/80">
              <span className="font-display text-title font-semibold">
                {storeCount}
              </span>{" "}
              {t("home.hero.storeCount", { count: storeCount })}
            </p>
          )}

          <div className="flex flex-wrap gap-3">
            <Link
              to="/products"
              className="rounded-pill bg-paper-raised px-5 py-3 font-semibold text-cedar transition hover:bg-cedar-subtle"
            >
              {t("home.hero.browseProducts")}
            </Link>

            <Link
              to="/stores"
              className="rounded-pill border border-on-cedar/30 px-5 py-3 font-semibold text-on-cedar transition hover:bg-on-cedar/10"
            >
              {t("home.hero.browseStores")}
            </Link>
          </div>
        </div>

        {/* The categories actually on the page, in the order they appear —
            not a fixed decorative list. */}
        <div className="rounded-card bg-on-cedar/10 p-6 backdrop-blur">
          <p className="text-small uppercase tracking-widest text-on-cedar/70">
            {t("home.categories.title")}
          </p>

          <div className="mt-4 grid grid-cols-2 gap-3">
            {sections.slice(0, 4).map((section) => (
              <Link
                key={section.category.id}
                to={`/products?category_id=${section.category.id}`}
                className="rounded-card bg-on-cedar/15 px-4 py-6 text-center font-medium transition hover:bg-on-cedar/25"
              >
                {localizedField(section.category, "name", i18n.language)}
              </Link>
            ))}
          </div>
        </div>
      </section>

      {/* Why the page is in this order — and how to change it. */}
      {!loading && sections.length > 0 && (
        <div className="flex flex-wrap items-center justify-between gap-3 rounded-card border border-line bg-paper-raised px-5 py-4">
          <p className="text-small text-ink-secondary">
            {personalized
              ? t("home.order.personalized")
              : t("home.order.default")}
          </p>

          {isAuthenticated && (
            <Link
              to="/settings/shopping"
              className="inline-flex items-center gap-2 text-small font-medium text-cedar hover:underline"
            >
              <SlidersHorizontal size={16} />
              {personalized
                ? t("home.order.edit")
                : t("home.order.choose")}
            </Link>
          )}
        </div>
      )}

      {loading ? (
        <div className="text-ink-muted">{t("home.loadingProducts")}</div>
      ) : (
        sections.map((section) => (
          <section key={section.category.id} className="space-y-5">
            <div className="flex items-end justify-between">
              <div>
                <h2 className="text-title font-bold">
                  {localizedField(section.category, "name", i18n.language)}
                </h2>

                {section.category.description && (
                  <p className="text-ink-muted">
                    {section.category.description}
                  </p>
                )}
              </div>

              <Link
                to={`/products?category_id=${section.category.id}`}
                className="shrink-0 font-medium text-cedar"
              >
                {t("home.featuredProducts.viewAll")}
              </Link>
            </div>

            <div className="grid gap-5 sm:grid-cols-2 lg:grid-cols-4">
              {section.products.map((product) => (
                <ProductCard key={product.id} product={product} />
              ))}
            </div>
          </section>
        ))
      )}

      {!loading && sections.length === 0 && (
        <section className="rounded-card border border-line bg-paper-raised p-6 shadow-card">
          <h2 className="text-title font-bold">{t("home.empty.title")}</h2>
          <p className="mt-2 text-ink-muted">{t("home.empty.description")}</p>
        </section>
      )}
    </div>
  );
}
