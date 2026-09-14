import { useTranslation } from "react-i18next";

import StarRating from "./StarRating";
import { formattingLocale } from "../../utils/helpers";

/**
 * Average + count. `compact` is the dense card variant (star, number,
 * "(N)"); the full variant adds a localised "N reviews" phrase.
 */
function RatingSummary({
  average,
  count,
  size = "md",
  compact = false,
  className = "",
}) {
  const { t, i18n } = useTranslation();
  const n = Number(count) || 0;
  const locale = formattingLocale(i18n.language);

  if (n === 0) {
    if (compact) return null;

    // A block, not an inline span. Every caller passes a top margin in
    // `className` (mt-2 / mt-3), and a vertical margin does nothing on an
    // inline box -- so on a product with no reviews yet this line sat
    // flush against the price above it, rendering as "$24.00No reviews
    // yet". The n > 0 branch below was already a block, which is why the
    // gap only ever went missing on unreviewed products.
    return (
      <div className={`text-small text-ink-faint ${className}`}>
        {t("reviews.none")}
      </div>
    );
  }

  const avg = Number(average) || 0;
  const avgText = new Intl.NumberFormat(locale, {
    minimumFractionDigits: 1,
    maximumFractionDigits: 1,
  }).format(avg);
  const countText = new Intl.NumberFormat(locale).format(n);

  if (compact) {
    return (
      <span
        dir="ltr"
        className={`inline-flex items-center gap-1 text-micro text-ink-muted ${className}`}
      >
        <StarRating value={avg} size="sm" />
        <span className="font-semibold text-ink-body">{avgText}</span>
        <span>({countText})</span>
      </span>
    );
  }

  return (
    <div className={`flex flex-wrap items-center gap-x-2 gap-y-1 ${className}`}>
      <span dir="ltr" className="inline-flex items-center gap-1.5">
        <StarRating value={avg} size={size} />
        <span className="font-semibold text-ink">{avgText}</span>
      </span>
      <span className="text-small text-ink-muted">
        {t("reviews.count", { count: n })}
      </span>
    </div>
  );
}

export default RatingSummary;
