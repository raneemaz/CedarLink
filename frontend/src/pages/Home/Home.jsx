import { useEffect, useState } from "react";
import { Link, useNavigate } from "react-router-dom";
import { useTranslation } from "react-i18next";
import { Search, SlidersHorizontal } from "lucide-react";

import api from "../../services/api";
import ProductCard from "../../components/product/ProductCard";
import { useAuth } from "../../context/AuthContext";
import { localizedField } from "../../utils/localize";

export default function Home() {
  const { t, i18n } = useTranslation();
  const { isAuthenticated } = useAuth();
  const navigate = useNavigate();

  const [sections, setSections] = useState([]);
  const [personalized, setPersonalized] = useState(false);
  const [loading, setLoading] = useState(true);
  // The chips are the distinct places CedarLink actually has stores in,
  // read from the stores endpoint. Not a fixed list, and not a number:
  // the hero makes no factual claim at all now, which retires the "120+"
  // problem rather than binding it to a real count of six.
  const [places, setPlaces] = useState([]);
  const [query, setQuery] = useState("");

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

        const stores = await api.get("/stores", { params: { limit: 100 } });
        if (!cancelled) {
          const seen = [];
          for (const store of stores.data?.stores || []) {
            const place = (store.location || "").trim();
            if (place && !seen.includes(place)) seen.push(place);
          }
          setPlaces(seen.slice(0, 6));
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
      {/*
        Search-first. The utility is the hero: it demonstrates search,
        the places CedarLink covers and open-now in one frame, and
        asserts nothing. Everything here is real — the chips are the
        distinct store locations the API returns, and there is no
        statistic, no decoration and no invented number.
      */}
      <section className="rounded-card border border-line bg-paper-raised px-6 py-14 text-center md:px-10">
        <h1 className="mx-auto max-w-3xl text-display font-semibold text-cedar-strong">
          {t("home.hero.title")}
        </h1>

        <form
          onSubmit={(event) => {
            event.preventDefault();
            const term = query.trim();
            navigate(term ? `/products?keyword=${encodeURIComponent(term)}` : "/products");
          }}
          className="mx-auto mt-8 flex w-full max-w-xl items-center gap-3 rounded-pill border-[1.5px] border-line bg-paper ps-5 pe-2 py-2 shadow-card focus-within:border-cedar-ring"
        >
          <Search size={18} className="shrink-0 text-ink-muted" aria-hidden="true" />

          <input
            type="search"
            value={query}
            onChange={(event) => setQuery(event.target.value)}
            aria-label={t("home.hero.searchLabel")}
            placeholder={t("home.hero.searchPlaceholder")}
            className="min-w-0 flex-1 bg-transparent py-2 text-body text-ink outline-none placeholder:text-ink-muted"
          />

          <button
            type="submit"
            className="shrink-0 rounded-pill bg-cedar px-5 py-2.5 text-small font-semibold text-on-cedar transition hover:bg-cedar-strong"
          >
            {t("home.hero.search")}
          </button>
        </form>

        <div className="mt-6 flex flex-wrap items-center justify-center gap-2">
          <Link
            to="/stores"
            className="inline-flex items-center gap-2 rounded-pill border border-cedar-ring bg-cedar-tint px-4 py-1.5 text-small font-semibold text-cedar-strong transition hover:bg-cedar-subtle"
          >
            <span className="h-1.5 w-1.5 rounded-pill bg-cedar" aria-hidden="true" />
            {t("home.hero.openNearMe")}
          </Link>

          {places.map((place) => (
            <Link
              key={place}
              to={`/stores?location=${encodeURIComponent(place)}`}
              className="rounded-pill border border-line bg-paper px-4 py-1.5 text-small font-semibold text-ink-body transition hover:border-cedar-ring hover:text-cedar"
            >
              {place}
            </Link>
          ))}
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
