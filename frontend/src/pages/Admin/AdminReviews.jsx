import { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { useTranslation } from "react-i18next";
import { toast } from "react-toastify";

import api from "../../services/api";
import ConfirmDialog from "../../components/common/ConfirmDialog/ConfirmDialog";
import StarRating from "../../components/reviews/StarRating";
import { formatDate } from "../../utils/helpers";

const FILTERS = ["queue", "flagged", "removed", "all"];
const PER_PAGE = 10;

const STATUS_BADGE = {
  published: "bg-emerald-100 text-emerald-700",
  flagged: "bg-amber-100 text-amber-700",
  removed: "bg-gray-200 text-gray-600",
};

// which actions each status allows
const ACTIONS = {
  published: ["flag", "remove"],
  flagged: ["remove", "restore"],
  removed: ["restore"],
};

const ACTION_VARIANT = { remove: "danger", flag: "danger", restore: "primary" };

function AdminReviews() {
  const { t, i18n } = useTranslation();

  const [filter, setFilter] = useState("queue");
  const [page, setPage] = useState(1);
  const [data, setData] = useState(null);
  const [loading, setLoading] = useState(true);
  const [reloadTick, setReloadTick] = useState(0);

  const [pending, setPending] = useState(null); // { review, action }
  const [reason, setReason] = useState("");
  const [working, setWorking] = useState(false);

  useEffect(() => {
    let cancelled = false;
    const run = async () => {
      setLoading(true);
      try {
        const res = await api.get("/admin/reviews", {
          params: { status: filter, page, limit: PER_PAGE },
        });
        if (!cancelled) setData(res.data);
      } catch (err) {
        if (!cancelled) {
          console.error("Failed to load review queue:", err);
          toast.error(t("adminReviews.errLoad"));
        }
      } finally {
        if (!cancelled) setLoading(false);
      }
    };
    run();
    return () => {
      cancelled = true;
    };
  }, [filter, page, reloadTick, t]);

  const runAction = async () => {
    if (!pending) return;
    setWorking(true);
    try {
      await api.patch(`/admin/reviews/${pending.review.id}`, {
        action: pending.action,
        reason: reason.trim() || null,
      });
      toast.success(t(`adminReviews.done.${pending.action}`));
      setPending(null);
      setReloadTick((n) => n + 1);
    } catch (err) {
      console.error("Moderation action failed:", err);
      toast.error(err.response?.data?.error || t("adminReviews.errAction"));
    } finally {
      setWorking(false);
    }
  };

  const openAction = (review, action) => {
    setReason("");
    setPending({ review, action });
  };

  const reviews = data?.reviews ?? [];
  const pages = data?.pages ?? 1;

  return (
    <div>
      <h1 className="mb-6 text-3xl font-bold text-gray-900">
        {t("adminReviews.title")}
      </h1>

      <div className="mb-4 flex flex-wrap gap-2">
        {FILTERS.map((key) => (
          <button
            key={key}
            type="button"
            onClick={() => {
              setFilter(key);
              setPage(1);
            }}
            className={`rounded-full px-4 py-1.5 text-sm font-medium transition ${
              filter === key
                ? "bg-emerald-700 text-white"
                : "bg-white text-gray-600 shadow-sm hover:bg-gray-50"
            }`}
          >
            {t(`adminReviews.filter.${key}`)}
          </button>
        ))}
      </div>

      {loading && !data ? (
        <p className="text-sm text-gray-500">{t("adminReviews.loading")}</p>
      ) : reviews.length === 0 ? (
        <div className="rounded-2xl bg-white py-16 text-center shadow-sm">
          <p className="text-gray-600">{t("adminReviews.empty")}</p>
        </div>
      ) : (
        <div className="space-y-4">
          {reviews.map((review) => (
            <article
              key={review.id}
              className="rounded-2xl bg-white p-5 shadow-sm"
            >
              <div className="flex flex-wrap items-center justify-between gap-2">
                <div className="flex flex-wrap items-center gap-2">
                  <StarRating value={review.rating} size="sm" />
                  <span
                    className={`rounded-full px-2.5 py-1 text-xs font-semibold ${
                      STATUS_BADGE[review.status]
                    }`}
                  >
                    {t(`reviewStatus.${review.status}`)}
                  </span>
                  <span className="text-sm text-gray-500">
                    {review.target.type === "product"
                      ? t("adminReviews.onProduct")
                      : t("adminReviews.onStore")}{" "}
                    <Link
                      to={
                        review.target.type === "product"
                          ? `/products/${review.target.id}`
                          : `/stores/${review.target.id}`
                      }
                      className="font-medium text-emerald-700 hover:underline"
                    >
                      {review.target.name || `#${review.target.id}`}
                    </Link>
                  </span>
                </div>
                <span className="text-xs text-gray-400">
                  {formatDate(review.created_at, i18n.language)}
                </span>
              </div>

              {review.title && (
                <p className="mt-3 font-medium text-gray-900">{review.title}</p>
              )}
              {review.body && (
                <p className="mt-1 whitespace-pre-line text-sm text-gray-600">
                  {review.body}
                </p>
              )}

              <p className="mt-3 text-xs text-gray-500">
                {t("adminReviews.byAuthor", {
                  name: review.author.name || t("reviews.anonymous"),
                  email: review.author.email || "—",
                })}
              </p>

              {review.reports.length > 0 && (
                <div className="mt-3 rounded-lg bg-amber-50 p-3">
                  <p className="text-xs font-semibold text-amber-800">
                    {t("adminReviews.reportsHeading", {
                      count: review.report_count,
                    })}
                  </p>
                  <ul className="mt-1 space-y-1">
                    {review.reports.map((r) => (
                      <li key={r.id} className="text-xs text-amber-900">
                        “{r.reason}” —{" "}
                        <span className="text-amber-700">
                          {r.reporter.name || t("reviews.anonymous")},{" "}
                          {formatDate(r.created_at, i18n.language)}
                        </span>
                      </li>
                    ))}
                  </ul>
                </div>
              )}

              {review.moderation_note && (
                <p className="mt-2 text-xs text-gray-400">
                  {t("adminReviews.lastNote", {
                    note: review.moderation_note,
                  })}
                </p>
              )}

              <div className="mt-4 flex gap-3 text-sm">
                {(ACTIONS[review.status] || []).map((action) => (
                  <button
                    key={action}
                    type="button"
                    onClick={() => openAction(review, action)}
                    className={`font-medium hover:underline ${
                      action === "restore"
                        ? "text-emerald-700"
                        : "text-red-600"
                    }`}
                  >
                    {t(`adminReviews.action.${action}`)}
                  </button>
                ))}
              </div>
            </article>
          ))}

          {pages > 1 && (
            <div className="flex items-center justify-between text-sm">
              <button
                type="button"
                onClick={() => setPage((p) => Math.max(1, p - 1))}
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
                onClick={() => setPage((p) => Math.min(pages, p + 1))}
                disabled={page >= pages}
                className="rounded-lg border border-gray-300 px-4 py-2 font-medium text-gray-700 hover:bg-gray-50 disabled:cursor-not-allowed disabled:opacity-50"
              >
                {t("common.next")}
              </button>
            </div>
          )}
        </div>
      )}

      <ConfirmDialog
        open={pending !== null}
        title={pending ? t(`adminReviews.confirmTitle.${pending.action}`) : ""}
        message={pending ? t(`adminReviews.confirmBody.${pending.action}`) : ""}
        confirmLabel={pending ? t(`adminReviews.action.${pending.action}`) : ""}
        variant={pending ? ACTION_VARIANT[pending.action] : "danger"}
        loading={working}
        onConfirm={runAction}
        onCancel={() => (working ? null : setPending(null))}
      >
        <label className="mb-1 block text-xs font-medium text-gray-600">
          {t("adminReviews.noteLabel")}
        </label>
        <textarea
          value={reason}
          onChange={(e) => setReason(e.target.value)}
          rows="2"
          maxLength={500}
          className="w-full resize-none rounded-lg border border-gray-300 px-3 py-2 text-sm outline-none focus:border-green-600 focus:ring-1 focus:ring-green-600"
        />
      </ConfirmDialog>
    </div>
  );
}

export default AdminReviews;
