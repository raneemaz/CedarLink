import { useState } from "react";
import { Star } from "lucide-react";
import { useTranslation } from "react-i18next";

const VALUES = [1, 2, 3, 4, 5];

/**
 * 1–5 star picker built on a native radio group, so keyboard support
 * (Tab to the group, arrow keys to move and select) comes for free. The
 * radios are visually hidden; focus shows a ring on the star via `peer`.
 *
 * dir="ltr" so arrow-key direction and fill order stay consistent under RTL.
 */
function StarRatingInput({ value = 0, onChange, name = "rating", disabled }) {
  const { t } = useTranslation();
  const [hover, setHover] = useState(0);
  const shown = hover || value || 0;

  return (
    <fieldset dir="ltr" disabled={disabled} className="inline-flex">
      <legend className="sr-only">{t("reviewForm.ratingLegend")}</legend>
      <div
        className="flex items-center gap-1"
        onMouseLeave={() => setHover(0)}
      >
        {VALUES.map((n) => (
          <label
            key={n}
            onMouseEnter={() => setHover(n)}
            className="cursor-pointer p-0.5"
          >
            <input
              type="radio"
              name={name}
              value={n}
              checked={value === n}
              onChange={() => onChange(n)}
              aria-label={t("reviewForm.starLabel", { count: n })}
              className="peer sr-only"
            />
            <Star
              size={28}
              strokeWidth={1.5}
              className={`rounded transition peer-focus-visible:outline peer-focus-visible:outline-2 peer-focus-visible:outline-offset-2 peer-focus-visible:outline-cedar-ring ${
                n <= shown
                  ? "fill-rating text-rating"
                  : "text-rating-empty"
              }`}
            />
          </label>
        ))}
      </div>
    </fieldset>
  );
}

export default StarRatingInput;
