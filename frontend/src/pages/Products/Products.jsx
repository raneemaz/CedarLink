import {
  useCallback,
  useEffect,
  useMemo,
  useRef,
  useState,
} from "react";
import { useSearchParams } from "react-router-dom";
import { useTranslation } from "react-i18next";
import { toast } from "react-toastify";

import ProductCard from "../../components/product/ProductCard";
import api from "../../services/api";
import { localizedName } from "../../utils/localize";

const SORT_OPTIONS = [
  { value: "", labelKey: "products.sortDefault" },
  { value: "newest", labelKey: "products.sortNewest" },
  { value: "rating", labelKey: "products.sortRating" },
  { value: "price_asc", labelKey: "products.sortPriceAsc" },
  { value: "price_desc", labelKey: "products.sortPriceDesc" },
];

const LIMIT_OPTIONS = [12, 24, 48];
const DEFAULT_LIMIT = 12;

const inputClass =
  "rounded-control border border-line-strong px-3 py-2 text-small outline-none " +
  "focus:border-cedar-ring";

function Products() {
  const { t, i18n } = useTranslation();
  const [searchParams, setSearchParams] = useSearchParams();

  const [categories, setCategories] = useState([]);
  const [stores, setStores] = useState([]);

  const [products, setProducts] = useState([]);
  const [page, setPage] = useState(1);
  const [pages, setPages] = useState(1);
  const [total, setTotal] = useState(0);
  const [loading, setLoading] = useState(true);

  // --- URL is the single source of filter truth --------------------------
  const urlKeyword = searchParams.get("keyword") || "";
  const categoryId = searchParams.get("category_id") || "";
  const storeId = searchParams.get("store_id") || "";
  const minPrice = searchParams.get("min_price") || "";
  const maxPrice = searchParams.get("max_price") || "";
  const inStock = searchParams.get("in_stock") === "true";
  const sort = searchParams.get("sort") || "";
  const limit = Number(searchParams.get("limit")) || DEFAULT_LIMIT;

  const setFilter = useCallback(
    (key, value) => {
      setSearchParams(
        (prev) => {
          const next = new URLSearchParams(prev);
          if (value === "" || value === null || value === undefined) {
            next.delete(key);
          } else {
            next.set(key, String(value));
          }
          if (key !== "page") next.delete("page");
          return next;
        },
        { replace: true },
      );
    },
    [setSearchParams],
  );

  const clearFilters = useCallback(
    () => setSearchParams({}, { replace: true }),
    [setSearchParams],
  );

  // The "hide out of stock" shopping preference is a default, not an
  // override: apply it only when the URL says nothing about in_stock.
  // Toggling the control sets in_stock explicitly (true/false), so this
  // runs at most once and never fights the user's choice.
  const prefChecked = useRef(false);

  useEffect(() => {
    if (prefChecked.current || searchParams.has("in_stock")) return;
    prefChecked.current = true;

    let userId = null;
    try {
      userId = JSON.parse(localStorage.getItem("user"))?.id ?? null;
    } catch {
      /* not logged in */
    }
    if (!userId) return;

    let cancelled = false;
    api
      .get(`/users/${userId}/shopping-preferences`)
      .then((response) => {
        if (
          !cancelled &&
          response.data?.shopping_preferences?.hide_out_of_stock
        ) {
          setFilter("in_stock", "true");
        }
      })
      .catch(() => {});

    return () => {
      cancelled = true;
    };
  }, [searchParams, setFilter]);

  // --- Debounced keyword input -----------------------------------------
  const [keywordDraft, setKeywordDraft] = useState(urlKeyword);

  useEffect(() => {
    setKeywordDraft(urlKeyword);
  }, [urlKeyword]);

  useEffect(() => {
    const handle = setTimeout(() => {
      if (keywordDraft.trim() !== urlKeyword) {
        setFilter("keyword", keywordDraft.trim());
      }
    }, 400);
    return () => clearTimeout(handle);
  }, [keywordDraft, urlKeyword, setFilter]);

  // --- Reference data ---------------------------------------------------
  useEffect(() => {
    let cancelled = false;
    (async () => {
      try {
        const [categoriesRes, storesRes] = await Promise.all([
          api.get("/categories"),
          api.get("/stores", { params: { limit: 100, sort: "name" } }),
        ]);
        if (cancelled) return;
        setCategories(categoriesRes.data || []);
        setStores(storesRes.data.stores || []);
      } catch (error) {
        if (!cancelled) console.error("Failed to load filters:", error);
      }
    })();
    return () => {
      cancelled = true;
    };
  }, []);

  // --- Products -------------------------------------------------------
  useEffect(() => {
    let cancelled = false;
    (async () => {
      setLoading(true);
      try {
        const params = Object.fromEntries(searchParams.entries());
        if (!params.limit) params.limit = DEFAULT_LIMIT;
        const response = await api.get("/products", { params });
        if (cancelled) return;
        setProducts(response.data.products || []);
        setPage(response.data.page || 1);
        setPages(response.data.pages || 1);
        setTotal(response.data.total || 0);
      } catch (error) {
        if (cancelled) return;
        console.error("Failed to fetch products:", error);
        toast.error(
          error.response?.data?.message || t("products.errLoad"),
        );
        setProducts([]);
      } finally {
        if (!cancelled) setLoading(false);
      }
    })();
    return () => {
      cancelled = true;
    };
  }, [searchParams, t]);

  const categoryName = useMemo(() => {
    const map = {};
    for (const category of categories) {
      map[String(category.id)] = localizedName(category, i18n.language);
    }
    return map;
  }, [categories, i18n.language]);

  const storeName = useMemo(() => {
    const map = {};
    for (const store of stores) map[String(store.id)] = store.name;
    return map;
  }, [stores]);

  const activeFilters = useMemo(() => {
    const parts = [];
    if (urlKeyword) {
      parts.push(t("products.filterKeyword", { value: urlKeyword }));
    }
    if (categoryId) {
      parts.push(
        t("products.filterCategory", {
          value: categoryName[categoryId] || categoryId,
        }),
      );
    }
    if (storeId) {
      parts.push(
        t("products.filterStore", {
          value: storeName[storeId] || storeId,
        }),
      );
    }
    if (minPrice) parts.push(t("products.filterMinPrice", { value: minPrice }));
    if (maxPrice) parts.push(t("products.filterMaxPrice", { value: maxPrice }));
    if (inStock) parts.push(t("products.filterInStock"));
    return parts;
  }, [
    t,
    urlKeyword,
    categoryId,
    storeId,
    minPrice,
    maxPrice,
    inStock,
    categoryName,
    storeName,
  ]);

  const hasActiveFilters = activeFilters.length > 0 || sort !== "";

  return (
    <div className="min-h-screen bg-paper px-2 py-2 lg:px-10">
      <div className="mx-auto max-w-screen-2xl">
        <div className="mb-6">
          <h1 className="text-title font-bold text-ink">
            {t("products.title")}
          </h1>
          <p className="mt-2 text-ink-muted">
            {t("products.subtitle")}
          </p>
        </div>

        {/* Filters */}
        <div className="mb-4 rounded-card bg-paper-raised p-4 shadow-card">
          <div className="grid gap-3 md:grid-cols-3 lg:grid-cols-4">
            <input
              type="text"
              value={keywordDraft}
              onChange={(event) => setKeywordDraft(event.target.value)}
              placeholder={t("products.searchPlaceholder")}
              className={`${inputClass} md:col-span-2`}
            />

            <select
              value={categoryId}
              onChange={(event) =>
                setFilter("category_id", event.target.value)
              }
              className={inputClass}
            >
              <option value="">{t("products.allCategories")}</option>
              {categories.map((category) => (
                <option key={category.id} value={category.id}>
                  {localizedName(category, i18n.language)}
                </option>
              ))}
            </select>

            <select
              value={storeId}
              onChange={(event) => setFilter("store_id", event.target.value)}
              className={inputClass}
            >
              <option value="">{t("products.allStores")}</option>
              {stores.map((store) => (
                <option key={store.id} value={store.id}>
                  {store.name}
                </option>
              ))}
            </select>

            <input
              type="number"
              min="0"
              value={minPrice}
              onChange={(event) =>
                setFilter("min_price", event.target.value)
              }
              placeholder={t("products.minPrice")}
              className={inputClass}
            />

            <input
              type="number"
              min="0"
              value={maxPrice}
              onChange={(event) =>
                setFilter("max_price", event.target.value)
              }
              placeholder={t("products.maxPrice")}
              className={inputClass}
            />

            <select
              value={sort}
              onChange={(event) => setFilter("sort", event.target.value)}
              className={inputClass}
            >
              {SORT_OPTIONS.map((option) => (
                <option key={option.value} value={option.value}>
                  {t(option.labelKey)}
                </option>
              ))}
            </select>

            <label className="flex items-center gap-2 px-1 text-small text-ink-body">
              <input
                type="checkbox"
                checked={inStock}
                onChange={(event) =>
                  setFilter(
                    "in_stock",
                    event.target.checked ? "true" : "false",
                  )
                }
                className="h-4 w-4 rounded border-line-strong text-cedar focus:ring-cedar-ring"
              />
              {t("products.inStockOnly")}
            </label>
          </div>

          <div className="mt-3 flex flex-wrap items-center justify-between gap-3 border-t border-line-subtle pt-3 text-small">
            <div className="flex items-center gap-3">
              <label className="text-ink-muted">
                {t("products.perPage")}{" "}
                <select
                  value={limit}
                  onChange={(event) =>
                    setFilter("limit", event.target.value)
                  }
                  className="ms-1 rounded border border-line-strong px-2 py-1"
                >
                  {LIMIT_OPTIONS.map((option) => (
                    <option key={option} value={option}>
                      {option}
                    </option>
                  ))}
                </select>
              </label>
            </div>

            <button
              type="button"
              onClick={clearFilters}
              disabled={!hasActiveFilters}
              className="rounded-control border border-line-strong px-3 py-1.5 font-medium text-ink-body hover:bg-paper disabled:cursor-not-allowed disabled:opacity-40"
            >
              {t("products.clearFilters")}
            </button>
          </div>
        </div>

        {/* Results */}
        {loading ? (
          <div className="py-20 text-center text-ink-muted">
            {t("products.loading")}
          </div>
        ) : products.length === 0 ? (
          <div className="rounded-card bg-paper-raised py-16 text-center shadow-card">
            <h2 className="text-title font-semibold text-ink-emphasis">
              {t("products.noneFound")}
            </h2>
            {activeFilters.length > 0 ? (
              <p className="mt-2 text-ink-muted">
                {t("products.activeFiltersLabel")}{" "}
                {activeFilters.join("، ")}
              </p>
            ) : (
              <p className="mt-2 text-ink-muted">
                {t("products.nothingToShow")}
              </p>
            )}
            {hasActiveFilters && (
              <button
                type="button"
                onClick={clearFilters}
                className="mt-4 rounded-control bg-cedar px-4 py-2 text-small font-medium text-on-cedar hover:bg-cedar-strong"
              >
                {t("products.clearFilters")}
              </button>
            )}
          </div>
        ) : (
          <>
            <p className="mb-3 text-small text-ink-muted">
              {t("products.count", { count: total })}
              {activeFilters.length > 0 && (
                <> · {activeFilters.join("، ")}</>
              )}
            </p>

            <div className="grid gap-6 sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4">
              {products.map((product) => (
                <ProductCard key={product.id} product={product} />
              ))}
            </div>

            {pages > 1 && (
              <div className="mt-6 flex items-center justify-between text-small">
                <button
                  type="button"
                  onClick={() => setFilter("page", page - 1)}
                  disabled={page <= 1}
                  className="rounded-control border border-line-strong px-4 py-2 font-medium text-ink-body hover:bg-paper disabled:cursor-not-allowed disabled:opacity-50"
                >
                  {t("common.previous")}
                </button>
                <span className="text-ink-muted">
                  {t("common.pageOf", { page, pages })}
                </span>
                <button
                  type="button"
                  onClick={() => setFilter("page", page + 1)}
                  disabled={page >= pages}
                  className="rounded-control border border-line-strong px-4 py-2 font-medium text-ink-body hover:bg-paper disabled:cursor-not-allowed disabled:opacity-50"
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

export default Products;
