import { useTranslation } from "react-i18next";

import StarRating from "./StarRating";
import { formatDate } from "../../utils/helpers";

/** One review's display: stars, author, date, optional title and body. */
function ReviewItem({ review }) {
  const { t, i18n } = useTranslation();
  const edited =
    review.updated_at && review.updated_at !== review.created_at;

  return (
    <article className="border-b border-gray-100 py-4 last:border-b-0">
      <div className="flex flex-wrap items-center gap-x-2 gap-y-1">
        <StarRating value={review.rating} size="sm" />
        <span className="text-sm font-medium text-gray-900">
          {review.author_name || t("reviews.anonymous")}
        </span>
        <span className="text-xs text-gray-400">
          {formatDate(review.created_at, i18n.language)}
          {edited && ` · ${t("reviews.edited")}`}
        </span>
      </div>

      {review.title && (
        <p className="mt-2 font-medium text-gray-900">{review.title}</p>
      )}
      {review.body && (
        <p className="mt-1 whitespace-pre-line text-sm leading-6 text-gray-600">
          {review.body}
        </p>
      )}
    </article>
  );
}

export default ReviewItem;
