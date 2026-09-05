import { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { useTranslation } from "react-i18next";
import { toast } from "react-toastify";

import api from "../../services/api";
import { localizedName } from "../../utils/localize";

function Categories() {
  const { t, i18n } = useTranslation();
  const [categories, setCategories] = useState([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    let cancelled = false;

    const load = async () => {
      try {
        const response = await api.get("/categories");
        if (!cancelled) setCategories(response.data || []);
      } catch (error) {
        if (cancelled) return;
        console.error("Failed to load categories:", error);
        toast.error(t("categoriesPage.errLoad"));
      } finally {
        if (!cancelled) setLoading(false);
      }
    };

    load();
    return () => {
      cancelled = true;
    };
  }, [t]);

  return (
    <div className="min-h-screen bg-surface px-6 py-10 lg:px-10">
      <div className="mx-auto max-w-5xl">
        <div className="mb-8">
          <h1 className="text-2xl font-bold text-text-primary">{t("categoriesPage.title")}</h1>
          <p className="mt-2 text-text-muted">
            {t("categoriesPage.subtitle")}
          </p>
        </div>

        {loading ? (
          <div className="py-20 text-center text-text-muted">
            {t("categoriesPage.loading")}
          </div>
        ) : categories.length === 0 ? (
          <div className="rounded-2xl bg-surface-raised py-20 text-center shadow-sm">
            <p className="text-text-muted">{t("categoriesPage.empty")}</p>
          </div>
        ) : (
          <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
            {categories.map((category) => (
              <Link
                key={category.id}
                to={`/products?category_id=${category.id}`}
                className="rounded-xl border border-border bg-surface-raised p-5 transition duration-200 hover:-translate-y-1 hover:shadow-md"
              >
                <h3 className="text-lg font-semibold text-text-primary">
                  {localizedName(category, i18n.language)}
                </h3>
                {category.description && (
                  <p className="mt-1 line-clamp-2 text-sm text-text-muted">
                    {category.description}
                  </p>
                )}
              </Link>
            ))}
          </div>
        )}
      </div>
    </div>
  );
}

export default Categories;
