import { Star } from "lucide-react";
import { useTranslation } from "react-i18next";

const SIZE_PX = { sm: 14, md: 18, lg: 22 };
const STARS = [0, 1, 2, 3, 4];

/**
 * Read-only star row with fractional fill (e.g. 4.6 -> 4 full + a 60% fifth).
 *
 * Pinned dir="ltr": a rating fills from the first star in every locale.
 * Letting the row flip under RTL would turn "4 out of 5" into "1 out of 5".
 */
function StarRating({ value = 0, size = "sm", className = "" }) {
  const { t } = useTranslation();
  const px = SIZE_PX[size] ?? SIZE_PX.sm;
  const clamped = Math.max(0, Math.min(5, Number(value) || 0));
  const fillPct = (clamped / 5) * 100;

  return (
    <span
      dir="ltr"
      role="img"
      aria-label={t("reviews.ratedOutOf", { value: clamped.toFixed(1) })}
      className={`relative inline-flex shrink-0 ${className}`}
      style={{ width: px * 5 }}
    >
      <span className="flex text-gray-300" aria-hidden="true">
        {STARS.map((i) => (
          <Star key={i} size={px} strokeWidth={1.5} className="shrink-0" />
        ))}
      </span>
      <span
        className="absolute inset-y-0 left-0 flex overflow-hidden text-amber-400"
        style={{ width: `${fillPct}%` }}
        aria-hidden="true"
      >
        {STARS.map((i) => (
          <Star
            key={i}
            size={px}
            strokeWidth={1.5}
            fill="currentColor"
            className="shrink-0"
          />
        ))}
      </span>
    </span>
  );
}

export default StarRating;
