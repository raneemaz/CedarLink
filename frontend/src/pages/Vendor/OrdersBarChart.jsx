import { useTranslation } from "react-i18next";

import { formatDate, formattingLocale } from "../../utils/helpers";

/**
 * Orders per day, drawn with CSS.
 *
 * No charting library: this is one bar chart of at most a year of daily
 * counts, and the smallest of them costs more transferred bytes than the
 * whole vendor console. A flex row of divs is the right size of tool.
 *
 * RTL comes free from the layout rather than from a flipped copy of it. A
 * flex row lays its children out along the inline axis, so under
 * `dir="rtl"` the first day is on the right and the series reads
 * right-to-left on its own. The axis follows with `border-s` / `border-b`
 * — logical sides, so the vertical axis lands on the right in Arabic and
 * the left in English, and neither is spelled out anywhere.
 */
function OrdersBarChart({ series, className = "" }) {
  const { t, i18n } = useTranslation();

  const counts = series.map((row) => row.orders);
  const max = Math.max(...counts, 0);

  const number = new Intl.NumberFormat(formattingLocale(i18n.language));

  const total = counts.reduce((sum, n) => sum + n, 0);

  // Every bar at zero would render an empty box with an axis, which reads
  // as broken rather than as empty. The caller shows a message instead.
  if (max === 0) {
    return (
      <p className={`text-sm text-text-muted ${className}`}>
        {t("vendorDashboard.chart.noOrdersInRange")}
      </p>
    );
  }

  const first = series[0];
  const last = series[series.length - 1];
  const middle = series[Math.floor(series.length / 2)];

  return (
    <figure className={className}>
      <div className="flex items-baseline justify-between">
        <figcaption className="text-sm font-medium text-text-body">
          {t("vendorDashboard.chart.title")}
        </figcaption>
        <span className="text-xs text-text-muted">
          {t("vendorDashboard.chart.peak", { count: max })}
        </span>
      </div>

      <div
        className="mt-3 flex h-40 items-end gap-px border-b border-s border-border ps-2 pb-0"
        role="img"
        aria-label={t("vendorDashboard.chart.summary", {
          count: total,
          from: formatDate(first.date, i18n.language),
          to: formatDate(last.date, i18n.language),
        })}
      >
        {series.map((row) => (
          <div
            key={row.date}
            className="flex h-full flex-1 items-end"
            // The only per-bar affordance a mouse user gets, and the only
            // place the exact figure lives outside the summary.
            title={`${formatDate(row.date, i18n.language)} — ${t(
              "vendorDashboard.chart.ordersCount",
              { count: row.orders },
            )}`}
          >
            <div
              className={`w-full rounded-t-sm ${
                row.orders > 0 ? "bg-brand-ring" : "bg-surface-sunken"
              }`}
              // A day with no orders still gets a hairline, so the axis
              // reads as a series with gaps rather than as missing data.
              style={{
                height: row.orders > 0
                  ? `${Math.max((row.orders / max) * 100, 4)}%`
                  : "2px",
              }}
            />
          </div>
        ))}
      </div>

      {/* justify-between follows the inline axis, so these three flip with
          the bars rather than needing their own RTL branch. */}
      <div className="mt-2 flex justify-between text-xs text-text-faint">
        <span>{formatDate(first.date, i18n.language)}</span>
        {series.length > 2 && (
          <span className="hidden sm:inline">
            {formatDate(middle.date, i18n.language)}
          </span>
        )}
        <span>{formatDate(last.date, i18n.language)}</span>
      </div>

      <p className="sr-only">
        {series
          .filter((row) => row.orders > 0)
          .map(
            (row) =>
              `${formatDate(row.date, i18n.language)}: ${number.format(
                row.orders,
              )}`,
          )
          .join(", ")}
      </p>
    </figure>
  );
}

export default OrdersBarChart;
