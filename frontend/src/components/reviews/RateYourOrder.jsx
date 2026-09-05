import { useEffect, useState } from "react";
import { useTranslation } from "react-i18next";
import { toast } from "react-toastify";
import { Pencil, Trash2 } from "lucide-react";

import api from "../../services/api";
import { localizedField } from "../../utils/localize";
import StarRating from "./StarRating";
import ReviewForm from "./ReviewForm";

function apiError(err, fallbackKey, t) {
  return (
    err.response?.data?.error ||
    err.response?.data?.message ||
    t(fallbackKey)
  );
}

/**
 * "Rate your order" — one row per product plus the store, driven by
 * GET /api/orders/{id}/reviewable. Already-reviewed rows show the review
 * with edit / delete; the rest offer a form.
 */
function RateYourOrder({ orderId }) {
  const { t, i18n } = useTranslation();

  const [data, setData] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const [reloadTick, setReloadTick] = useState(0);

  const [openKey, setOpenKey] = useState(null);
  const [saving, setSaving] = useState(false);
  const [formError, setFormError] = useState("");

  const refresh = () => setReloadTick((n) => n + 1);

  useEffect(() => {
    let cancelled = false;

    const run = async () => {
      setLoading(true);
      setError("");
      try {
        const res = await api.get(`/orders/${orderId}/reviewable`);
        if (!cancelled) setData(res.data);
      } catch (err) {
        if (!cancelled) {
          console.error("Failed to load reviewable targets:", err);
          setError(apiError(err, "rateOrder.loadError", t));
        }
      } finally {
        if (!cancelled) setLoading(false);
      }
    };

    run();
    return () => {
      cancelled = true;
    };
  }, [orderId, reloadTick, t]);

  const closeForm = () => {
    setOpenKey(null);
    setFormError("");
  };

  const createReview = async (targetField, targetId, values) => {
    setSaving(true);
    setFormError("");
    try {
      await api.post("/reviews", {
        order_id: orderId,
        [targetField]: targetId,
        ...values,
      });
      toast.success(t("rateOrder.submitted"));
      closeForm();
      refresh();
    } catch (err) {
      console.error("Failed to submit review:", err);
      setFormError(apiError(err, "rateOrder.submitError", t));
    } finally {
      setSaving(false);
    }
  };

  const editReview = async (reviewId, values) => {
    setSaving(true);
    setFormError("");
    try {
      await api.put(`/reviews/${reviewId}`, values);
      toast.success(t("rateOrder.updated"));
      closeForm();
      refresh();
    } catch (err) {
      console.error("Failed to update review:", err);
      setFormError(apiError(err, "rateOrder.submitError", t));
    } finally {
      setSaving(false);
    }
  };

  const deleteReview = async (reviewId) => {
    if (!window.confirm(t("rateOrder.confirmDelete"))) return;
    try {
      await api.delete(`/reviews/${reviewId}`);
      toast.success(t("rateOrder.deleted"));
      refresh();
    } catch (err) {
      console.error("Failed to delete review:", err);
      toast.error(apiError(err, "rateOrder.deleteError", t));
    }
  };

  if (loading && !data) {
    return (
      <div className="rounded-2xl border border-border bg-surface-raised p-6 shadow-sm">
        <p className="text-sm text-text-muted">{t("rateOrder.loading")}</p>
      </div>
    );
  }
  if (error) {
    return (
      <div className="rounded-2xl border border-border bg-surface-raised p-6 shadow-sm">
        <p className="text-sm text-danger">{error}</p>
      </div>
    );
  }
  if (!data?.can_review) return null;

  const rows = [
    ...data.products.map((p) => ({
      key: `p:${p.id}`,
      label: localizedField(p, "name", i18n.language) || t("rateOrder.product"),
      targetField: "product_id",
      targetId: p.id,
      review: p.review,
    })),
    {
      key: "store",
      label: t("rateOrder.storeRow", { store: data.store.name }),
      targetField: "store_id",
      targetId: data.store.id,
      review: data.store.review,
    },
  ];

  return (
    <div className="rounded-2xl border border-border bg-surface-raised shadow-sm">
      <div className="border-b border-border p-6">
        <h2 className="text-xl font-semibold text-text-primary">
          {t("rateOrder.heading")}
        </h2>
        <p className="mt-1 text-sm text-text-muted">{t("rateOrder.subtitle")}</p>
      </div>

      <ul className="divide-y divide-border-subtle">
        {rows.map((row) => {
          const isOpen = openKey === row.key;
          return (
            <li key={row.key} className="p-6">
              <p className="font-medium text-text-primary">{row.label}</p>

              {isOpen ? (
                <div className="mt-3">
                  <ReviewForm
                    initial={row.review || undefined}
                    submitting={saving}
                    error={formError}
                    onCancel={closeForm}
                    onSubmit={(values) =>
                      row.review
                        ? editReview(row.review.id, values)
                        : createReview(row.targetField, row.targetId, values)
                    }
                  />
                </div>
              ) : row.review?.status === "removed" ? (
                <p className="mt-2 text-sm text-text-muted">
                  {t("rateOrder.removed")}
                </p>
              ) : row.review ? (
                <div className="mt-2">
                  <div className="flex flex-wrap items-center gap-2">
                    <StarRating value={row.review.rating} size="sm" />
                    {row.review.title && (
                      <span className="text-sm font-medium text-text-emphasis">
                        {row.review.title}
                      </span>
                    )}
                  </div>
                  {row.review.body && (
                    <p className="mt-1 whitespace-pre-line text-sm text-text-secondary">
                      {row.review.body}
                    </p>
                  )}
                  <div className="mt-2 flex gap-3 text-sm">
                    <button
                      type="button"
                      onClick={() => {
                        setFormError("");
                        setOpenKey(row.key);
                      }}
                      className="inline-flex items-center gap-1 font-medium text-brand hover:underline"
                    >
                      <Pencil className="h-3.5 w-3.5" />
                      {t("rateOrder.edit")}
                    </button>
                    <button
                      type="button"
                      onClick={() => deleteReview(row.review.id)}
                      className="inline-flex items-center gap-1 font-medium text-danger hover:underline"
                    >
                      <Trash2 className="h-3.5 w-3.5" />
                      {t("rateOrder.delete")}
                    </button>
                  </div>
                </div>
              ) : (
                <button
                  type="button"
                  onClick={() => {
                    setFormError("");
                    setOpenKey(row.key);
                  }}
                  className="mt-2 rounded-lg border border-brand px-3 py-1.5 text-sm font-medium text-brand transition hover:bg-brand hover:text-on-brand"
                >
                  {t("rateOrder.write")}
                </button>
              )}
            </li>
          );
        })}
      </ul>
    </div>
  );
}

export default RateYourOrder;
