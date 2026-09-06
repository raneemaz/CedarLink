import { useEffect, useMemo, useState } from "react";
import { useTranslation } from "react-i18next";
import { BarChart3, Info, Truck } from "lucide-react";

import api from "../../services/api";
import { formatDate, formattingLocale } from "../../utils/helpers";
import { localizedField } from "../../utils/localize";
import OrdersBarChart from "./OrdersBarChart";

const PRESETS = [7, 30, 90];

const STATUSES = ["pending", "processing", "delivered", "canceled"];

const STATUS_TONE = {
  pending: "bg-warning-subtle text-warning",
  processing: "bg-info-subtle text-info",
  delivered: "bg-paper-sunken text-cedar-strong",
  canceled: "bg-paper-sunken text-ink-secondary",
};

/**
 * Money, as a fixed `$X.XX` string.
 *
 * Deliberately not locale-formatted: ADR 0010 keeps transactional and
 * total money in a stable, universally legible format, and the server
 * already sends these as fixed two-decimal strings so nothing here
 * rounds anything.
 */
function money(value) {
  return `$${value}`;
}

function Card({ label, value, hint, tone = "", icon: Icon }) {
  return (
    <div className={`rounded-card border border-line bg-paper-raised p-5 ${tone}`}>
      <div className="flex items-center gap-2">
        {Icon && <Icon size={15} className="shrink-0 text-ink-faint" />}
        <p className="text-micro font-medium uppercase tracking-wide text-ink-muted">
          {label}
        </p>
      </div>

      <p className="mt-2 text-title font-bold text-ink" dir="ltr">
        {value}
      </p>

      {hint && <p className="mt-1 text-micro text-ink-muted">{hint}</p>}
    </div>
  );
}

function ProductTable({ title, caption, rows, measure, language }) {
  const { t } = useTranslation();

  return (
    <div className="rounded-card border border-line bg-paper-raised">
      <div className="border-b border-line-subtle px-5 py-4">
        <h2 className="font-semibold text-ink">{title}</h2>
        <p className="mt-1 text-micro text-ink-muted">{caption}</p>
      </div>

      {rows.length === 0 ? (
        <p className="px-5 py-6 text-small text-ink-muted">
          {t("vendorDashboard.tables.nothingSold")}
        </p>
      ) : (
        <ol className="divide-y divide-line-subtle">
          {rows.map((row, index) => (
            <li
              key={row.id}
              className="flex items-center gap-3 px-5 py-3 text-small"
            >
              <span className="w-5 shrink-0 text-micro text-ink-faint">
                {index + 1}
              </span>

              <span className="min-w-0 flex-1 truncate text-ink-emphasis">
                {localizedField(row, "name", language)}
              </span>

              <span className="shrink-0 font-medium text-ink" dir="ltr">
                {measure(row)}
              </span>
            </li>
          ))}
        </ol>
      )}
    </div>
  );
}

/** The last `days` days, ending today, as ISO dates. */
function rangeForPreset(days) {
  const to = new Date();
  const from = new Date();
  from.setDate(to.getDate() - (days - 1));

  const iso = (d) => d.toISOString().slice(0, 10);

  return { preset: days, from: iso(from), to: iso(to) };
}

function VendorDashboard() {
  const { t, i18n } = useTranslation();

  // The chosen period is state the vendor set, not something an effect
  // derives — so the effect below only fetches, and never calls setState
  // synchronously in its own body.
  const [range, setRange] = useState(() => rangeForPreset(30));
  const [custom, setCustom] = useState({ from: "", to: "" });

  const [result, setResult] = useState({ key: null, data: null, error: "" });

  const key = `${range.from}:${range.to}`;
  // Derived, not stored: we are loading exactly while the answer we hold
  // is for a different period than the one selected.
  const loading = result.key !== key;

  const data = result.data;
  const error = result.error;

  const number = useMemo(
    () => new Intl.NumberFormat(formattingLocale(i18n.language)),
    [i18n.language],
  );

  useEffect(() => {
    let cancelled = false;

    api
      .get("/vendor/dashboard", {
        params: { from: range.from, to: range.to },
      })
      .then(({ data: body }) => {
        if (!cancelled) setResult({ key, data: body, error: "" });
      })
      .catch((err) => {
        console.error("Failed to load the dashboard:", err);
        if (!cancelled) {
          setResult({
            key,
            data: null,
            error: err.response?.data?.message || "loadError",
          });
        }
      });

    return () => {
      cancelled = true;
    };
  }, [key, range.from, range.to]);

  const preset = range.preset;

  const applyCustom = (event) => {
    event.preventDefault();
    if (!custom.from || !custom.to) return;
    setRange({ preset: null, from: custom.from, to: custom.to });
  };

  const header = (
    <div>
      <h1 className="text-title font-bold text-ink">
        {t("vendorDashboard.title")}
      </h1>
      <p className="mt-1 text-small text-ink-muted">
        {t("vendorDashboard.subtitle")}
      </p>
    </div>
  );

  const periodSelector = (
    <div className="mt-6 flex flex-wrap items-end gap-4 rounded-card border border-line bg-paper-raised p-4">
      <div className="flex flex-wrap gap-2">
        {PRESETS.map((days) => (
          <button
            key={days}
            type="button"
            onClick={() => {
              setCustom({ from: "", to: "" });
              setRange(rangeForPreset(days));
            }}
            className={`cursor-pointer rounded-control px-3 py-2 text-small transition ${
              preset === days
                ? "bg-cedar font-medium text-on-cedar"
                : "border border-line-strong text-ink-body hover:bg-paper"
            }`}
          >
            {t("vendorDashboard.period.lastDays", { count: days })}
          </button>
        ))}
      </div>

      <form onSubmit={applyCustom} className="flex flex-wrap items-end gap-2">
        <div>
          <label
            htmlFor="range-from"
            className="mb-1 block text-micro text-ink-muted"
          >
            {t("vendorDashboard.period.from")}
          </label>
          <input
            id="range-from"
            type="date"
            value={custom.from}
            onChange={(e) =>
              setCustom((prev) => ({ ...prev, from: e.target.value }))
            }
            className="rounded-control border border-line-strong px-3 py-2 text-small"
          />
        </div>

        <div>
          <label
            htmlFor="range-to"
            className="mb-1 block text-micro text-ink-muted"
          >
            {t("vendorDashboard.period.to")}
          </label>
          <input
            id="range-to"
            type="date"
            value={custom.to}
            onChange={(e) =>
              setCustom((prev) => ({ ...prev, to: e.target.value }))
            }
            className="rounded-control border border-line-strong px-3 py-2 text-small"
          />
        </div>

        <button
          type="submit"
          disabled={!custom.from || !custom.to}
          className="cursor-pointer rounded-control border border-line-strong px-3 py-2 text-small text-ink-body transition hover:bg-paper disabled:cursor-not-allowed disabled:opacity-50"
        >
          {t("vendorDashboard.period.apply")}
        </button>
      </form>
    </div>
  );

  if (loading && !data) {
    return (
      <div>
        {header}
        <p className="mt-8 text-small text-ink-muted">
          {t("vendorDashboard.loading")}
        </p>
      </div>
    );
  }

  if (error) {
    return (
      <div>
        {header}
        <div className="mt-8 rounded-card border border-danger-border bg-danger-subtle p-5 text-small text-danger-strong">
          {error === "loadError" ? t("vendorDashboard.loadError") : error}
        </div>
      </div>
    );
  }

  const collected = data.money.collected;
  const inProgress = data.money.in_progress;

  // Two different nothings. No orders at all is a new store and needs an
  // explanation; orders with none delivered yet is a working store whose
  // money has not arrived, and the cards are true as they stand.
  const nothingYet = !data.has_orders;
  const nothingCollected = data.has_orders && collected.orders === 0;

  return (
    <div>
      {header}
      {periodSelector}

      <p className="mt-4 text-micro text-ink-faint">
        {t("vendorDashboard.showingRange", {
          from: formatDate(data.range.from, i18n.language),
          to: formatDate(data.range.to, i18n.language),
        })}
      </p>

      {nothingYet ? (
        <div className="mt-6 rounded-card border border-dashed border-line-strong bg-paper-raised p-10 text-center">
          <BarChart3 size={30} className="mx-auto text-ink-disabled" />
          <h2 className="mt-4 text-body font-semibold text-ink">
            {t("vendorDashboard.empty.title")}
          </h2>
          <p className="mx-auto mt-2 max-w-md text-small text-ink-muted">
            {t("vendorDashboard.empty.body")}
          </p>
        </div>
      ) : (
        <>
          {nothingCollected && (
            <p className="mt-6 flex items-start gap-2 rounded-card bg-info-subtle px-4 py-3 text-small text-info">
              <Info size={16} className="mt-0.5 shrink-0" />
              {t("vendorDashboard.nothingDeliveredYet")}
            </p>
          )}

          {/* Money in hand. Cash on delivery, so this is what has actually
              been collected — never mixed with what is still coming. */}
          <h2 className="mt-8 text-small font-semibold uppercase tracking-wide text-ink-muted">
            {t("vendorDashboard.collected.heading")}
          </h2>

          <div className="mt-3 grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
            <Card
              label={t("vendorDashboard.collected.revenue")}
              value={money(collected.revenue)}
              hint={t("vendorDashboard.collected.revenueHint")}
              tone="ring-1 ring-cedar-tint"
            />
            <Card
              label={t("vendorDashboard.collected.goods")}
              value={money(collected.goods_sold)}
              hint={t("vendorDashboard.collected.goodsHint")}
            />
            <Card
              label={t("vendorDashboard.collected.discounts")}
              // Signed only when there is something to sign: "−$0.00"
              // reads as a bug rather than as nothing given away.
              value={
                Number(collected.discounts) > 0
                  ? `−${money(collected.discounts)}`
                  : money(collected.discounts)
              }
              hint={t("vendorDashboard.collected.discountsHint")}
            />
            <Card
              icon={Truck}
              label={t("vendorDashboard.collected.delivery")}
              value={money(collected.delivery)}
              hint={t("vendorDashboard.collected.deliveryHint")}
              tone="border-dashed bg-paper"
            />
          </div>

          <div className="mt-4 grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
            <Card
              label={t("vendorDashboard.totals.orders")}
              value={number.format(data.totals.orders)}
              hint={t("vendorDashboard.totals.ordersHint")}
            />
            <Card
              label={t("vendorDashboard.totals.units")}
              value={number.format(data.totals.units_sold)}
              hint={t("vendorDashboard.totals.unitsHint")}
            />
            <Card
              label={t("vendorDashboard.totals.average")}
              value={money(data.totals.average_order_value)}
              hint={t("vendorDashboard.totals.averageHint")}
            />
            <Card
              label={t("vendorDashboard.inProgress.revenue")}
              value={money(inProgress.revenue)}
              hint={t("vendorDashboard.inProgress.revenueHint", {
                count: inProgress.orders,
              })}
              tone="border-dashed"
            />
          </div>

          {/* Chart */}
          <div className="mt-8 rounded-card border border-line bg-paper-raised p-5">
            <OrdersBarChart series={data.orders_per_day} />

            {data.busiest_day && (
              <p className="mt-4 text-small text-ink-secondary">
                {t("vendorDashboard.chart.busiest", {
                  date: formatDate(data.busiest_day.date, i18n.language),
                  count: data.busiest_day.orders,
                })}
              </p>
            )}
          </div>

          {/* Status breakdown */}
          <div className="mt-8 rounded-card border border-line bg-paper-raised p-5">
            <h2 className="font-semibold text-ink">
              {t("vendorDashboard.status.title")}
            </h2>

            <dl className="mt-4 grid gap-3 sm:grid-cols-4">
              {STATUSES.map((status) => (
                <div
                  key={status}
                  className={`rounded-control px-4 py-3 ${STATUS_TONE[status]}`}
                >
                  <dt className="text-micro font-medium">
                    {t(`orderStatus.${status}`)}
                  </dt>
                  <dd className="mt-1 text-title font-bold" dir="ltr">
                    {number.format(data.orders_by_status[status])}
                  </dd>
                </div>
              ))}
            </dl>
          </div>

          {/* The two top-product tables, side by side on purpose: the
              difference between them is the thing worth seeing. */}
          <div className="mt-8 grid gap-4 lg:grid-cols-2">
            <ProductTable
              title={t("vendorDashboard.tables.byUnits")}
              caption={t("vendorDashboard.tables.byUnitsCaption")}
              rows={data.top_products_by_units}
              measure={(row) =>
                t("vendorDashboard.tables.units", { count: row.units })
              }
              language={i18n.language}
            />

            <ProductTable
              title={t("vendorDashboard.tables.byRevenue")}
              caption={t("vendorDashboard.tables.byRevenueCaption")}
              rows={data.top_products_by_revenue}
              measure={(row) => money(row.revenue)}
              language={i18n.language}
            />
          </div>

          {/* Best rated */}
          <div className="mt-4 rounded-card border border-line bg-paper-raised">
            <div className="border-b border-line-subtle px-5 py-4">
              <h2 className="font-semibold text-ink">
                {t("vendorDashboard.tables.bestRated")}
              </h2>
              <p className="mt-1 text-micro text-ink-muted">
                {t("vendorDashboard.tables.bestRatedCaption")}
              </p>
            </div>

            {data.best_rated_products.length === 0 ? (
              <p className="px-5 py-6 text-small text-ink-muted">
                {t("vendorDashboard.tables.notEnoughReviews")}
              </p>
            ) : (
              <ol className="divide-y divide-line-subtle">
                {data.best_rated_products.map((row, index) => (
                  <li
                    key={row.id}
                    className="flex items-center gap-3 px-5 py-3 text-small"
                  >
                    <span className="w-5 shrink-0 text-micro text-ink-faint">
                      {index + 1}
                    </span>
                    <span className="min-w-0 flex-1 truncate text-ink-emphasis">
                      {localizedField(row, "name", i18n.language)}
                    </span>
                    <span
                      className="shrink-0 font-medium text-ink"
                      dir="ltr"
                    >
                      {row.rating_avg?.toFixed(1)}
                    </span>
                    <span className="shrink-0 text-micro text-ink-faint">
                      {t("vendorDashboard.tables.reviews", {
                        count: row.rating_count,
                      })}
                    </span>
                  </li>
                ))}
              </ol>
            )}
          </div>
        </>
      )}
    </div>
  );
}

export default VendorDashboard;
