import { useEffect, useState } from "react";
import { useTranslation } from "react-i18next";

import api from "../../services/api";
import ReviewItem from "./ReviewItem";

const PER_PAGE = 5;

const pagerClass =
  "rounded-lg border border-gray-300 px-3 py-1.5 font-medium text-gray-700 " +
  "hover:bg-gray-50 disabled:cursor-not-allowed disabled:opacity-50";

/**
 * Paginated published-review list for a product or store. `endpoint` is
 * e.g. `/products/42/reviews`. Renders an explicit empty state.
 */
function ReviewList({ endpoint }) {
  const { t } = useTranslation();
  const [page, setPage] = useState(1);
  const [data, setData] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");

  useEffect(() => {
    let cancelled = false;

    const run = async () => {
      setLoading(true);
      setError("");
      try {
        const res = await api.get(endpoint, {
          params: { page, limit: PER_PAGE },
        });
        if (!cancelled) setData(res.data);
      } catch (err) {
        if (!cancelled) {
          console.error("Failed to load reviews:", err);
          setError(t("reviews.loadError"));
        }
      } finally {
        if (!cancelled) setLoading(false);
      }
    };

    run();
    return () => {
      cancelled = true;
    };
  }, [endpoint, page, t]);

  if (loading && !data) {
    return <p className="text-sm text-gray-400">{t("reviews.loading")}</p>;
  }
  if (error) {
    return <p className="text-sm text-red-600">{error}</p>;
  }

  const reviews = data?.reviews ?? [];
  if (reviews.length === 0) {
    return (
      <div className="rounded-xl border border-dashed border-gray-200 px-6 py-10 text-center">
        <p className="text-sm font-medium text-gray-600">
          {t("reviews.emptyTitle")}
        </p>
        <p className="mt-1 text-xs text-gray-400">{t("reviews.emptyBody")}</p>
      </div>
    );
  }

  const pages = data?.pages ?? 1;

  return (
    <div>
      <div>
        {reviews.map((review) => (
          <ReviewItem key={review.id} review={review} />
        ))}
      </div>

      {pages > 1 && (
        <div className="mt-4 flex items-center justify-between text-sm">
          <button
            type="button"
            onClick={() => setPage((p) => Math.max(1, p - 1))}
            disabled={page <= 1}
            className={pagerClass}
          >
            {t("common.previous")}
          </button>
          <span className="text-gray-500">
            {t("common.pageOf", { page, pages })}
          </span>
          <button
            type="button"
            onClick={() => setPage((p) => Math.min(pages, p + 1))}
            disabled={page >= pages}
            className={pagerClass}
          >
            {t("common.next")}
          </button>
        </div>
      )}
    </div>
  );
}

export default ReviewList;
