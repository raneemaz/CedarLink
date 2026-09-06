import { useState } from "react";
import { useTranslation } from "react-i18next";
import { toast } from "react-toastify";
import { Flag } from "lucide-react";

import api from "../../services/api";
import { useAuth } from "../../context/AuthContext";
import ConfirmDialog from "../common/ConfirmDialog/ConfirmDialog";
import StarRating from "./StarRating";
import { formatDate } from "../../utils/helpers";

/** One review's display: stars, author, date, optional title and body,
 *  plus a discreet report control for signed-in users. */
function ReviewItem({ review }) {
  const { t, i18n } = useTranslation();
  const { isAuthenticated } = useAuth();

  const [dialogOpen, setDialogOpen] = useState(false);
  const [reason, setReason] = useState("");
  const [submitting, setSubmitting] = useState(false);
  const [reported, setReported] = useState(false);

  const edited =
    review.updated_at && review.updated_at !== review.created_at;

  const submitReport = async () => {
    if (!reason.trim()) return;
    setSubmitting(true);
    try {
      await api.post(`/reviews/${review.id}/report`, {
        reason: reason.trim(),
      });
      toast.success(t("reviewReport.sent"));
      setReported(true);
      setDialogOpen(false);
    } catch (err) {
      const code = err.response?.data?.code;
      if (code === "already_reported") {
        setReported(true);
        setDialogOpen(false);
        toast.info(t("reviewReport.already"));
      } else {
        toast.error(
          err.response?.data?.error || t("reviewReport.error"),
        );
      }
    } finally {
      setSubmitting(false);
    }
  };

  return (
    <article className="border-b border-line-subtle py-4 last:border-b-0">
      <div className="flex flex-wrap items-center gap-x-2 gap-y-1">
        <StarRating value={review.rating} size="sm" />
        <span className="text-small font-medium text-ink">
          {review.author_name || t("reviews.anonymous")}
        </span>
        <span className="text-micro text-ink-faint">
          {formatDate(review.created_at, i18n.language)}
          {edited && ` · ${t("reviews.edited")}`}
        </span>
      </div>

      {review.title && (
        <p className="mt-2 font-medium text-ink">{review.title}</p>
      )}
      {review.body && (
        <p className="mt-1 whitespace-pre-line text-small leading-6 text-ink-secondary">
          {review.body}
        </p>
      )}

      {isAuthenticated && (
        <div className="mt-2">
          {reported ? (
            <span className="text-micro text-ink-faint">
              {t("reviewReport.reported")}
            </span>
          ) : (
            <button
              type="button"
              onClick={() => {
                setReason("");
                setDialogOpen(true);
              }}
              className="inline-flex items-center gap-1 text-micro text-ink-faint transition hover:text-danger"
            >
              <Flag className="h-3 w-3" />
              {t("reviewReport.action")}
            </button>
          )}
        </div>
      )}

      <ConfirmDialog
        open={dialogOpen}
        title={t("reviewReport.title")}
        message={t("reviewReport.prompt")}
        confirmLabel={t("reviewReport.confirm")}
        variant="danger"
        loading={submitting}
        confirmDisabled={!reason.trim()}
        onConfirm={submitReport}
        onCancel={() => (submitting ? null : setDialogOpen(false))}
      >
        <label
          htmlFor={`report-reason-${review.id}`}
          className="mb-1 block text-micro font-medium text-ink-secondary"
        >
          {t("reviewReport.reasonLabel")}
        </label>
        <textarea
          id={`report-reason-${review.id}`}
          rows="3"
          maxLength={500}
          value={reason}
          onChange={(e) => setReason(e.target.value)}
          className="w-full resize-none rounded-control border border-line-strong px-3 py-2 text-small outline-none focus:border-cedar-ring focus:ring-1 focus:ring-cedar-ring"
        />
      </ConfirmDialog>
    </article>
  );
}

export default ReviewItem;
