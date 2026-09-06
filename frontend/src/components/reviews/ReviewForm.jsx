import { useState } from "react";
import { useTranslation } from "react-i18next";

import Button from "../common/Button/Button";
import StarRatingInput from "./StarRatingInput";

const TITLE_MAX = 120;
const BODY_MAX = 2000;

const fieldClass =
  "w-full rounded-lg border border-line-strong px-3 py-2 text-sm outline-none " +
  "focus:border-cedar-ring focus:ring-1 focus:ring-cedar-ring";

/**
 * Create / edit form for one review. `initial` pre-fills it for an edit.
 * `onSubmit({ rating, title, body })` — title / body are trimmed strings
 * or null. Rating is required (1–5); the rest is optional.
 */
function ReviewForm({ initial, onSubmit, onCancel, submitting, error }) {
  const { t } = useTranslation();
  const [rating, setRating] = useState(initial?.rating ?? 0);
  const [title, setTitle] = useState(initial?.title ?? "");
  const [body, setBody] = useState(initial?.body ?? "");
  const [showRatingError, setShowRatingError] = useState(false);

  const submit = (event) => {
    event.preventDefault();
    if (!rating) {
      setShowRatingError(true);
      return;
    }
    onSubmit({
      rating,
      title: title.trim() || null,
      body: body.trim() || null,
    });
  };

  const counter = (len, max) =>
    t("reviewForm.counter", { current: len, max });

  return (
    <form onSubmit={submit} className="space-y-4">
      <div>
        <p className="mb-1 text-sm font-medium text-ink-body">
          {t("reviewForm.ratingLabel")}
        </p>
        <StarRatingInput
          value={rating}
          onChange={(n) => {
            setRating(n);
            setShowRatingError(false);
          }}
          disabled={submitting}
        />
        {showRatingError && (
          <p className="mt-1 text-xs text-danger">
            {t("reviewForm.ratingRequired")}
          </p>
        )}
      </div>

      <div>
        <label
          htmlFor="review-title"
          className="mb-1 block text-sm font-medium text-ink-body"
        >
          {t("reviewForm.titleLabel")}
        </label>
        <input
          id="review-title"
          type="text"
          maxLength={TITLE_MAX}
          value={title}
          onChange={(e) => setTitle(e.target.value)}
          disabled={submitting}
          className={fieldClass}
        />
        <p className="mt-1 text-xs text-ink-faint text-end">
          {counter(title.length, TITLE_MAX)}
        </p>
      </div>

      <div>
        <label
          htmlFor="review-body"
          className="mb-1 block text-sm font-medium text-ink-body"
        >
          {t("reviewForm.bodyLabel")}
        </label>
        <textarea
          id="review-body"
          rows="3"
          maxLength={BODY_MAX}
          value={body}
          onChange={(e) => setBody(e.target.value)}
          disabled={submitting}
          className={`resize-none ${fieldClass}`}
        />
        <p className="mt-1 text-xs text-ink-faint text-end">
          {counter(body.length, BODY_MAX)}
        </p>
      </div>

      {error && <p className="text-sm text-danger">{error}</p>}

      <div className="flex gap-2">
        <Button type="submit" disabled={submitting}>
          {submitting ? t("reviewForm.saving") : t("reviewForm.submit")}
        </Button>
        {onCancel && (
          <Button
            type="button"
            variant="secondary"
            onClick={onCancel}
            disabled={submitting}
          >
            {t("reviewForm.cancel")}
          </Button>
        )}
      </div>
    </form>
  );
}

export default ReviewForm;
