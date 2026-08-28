// Shared helpers.

export type RateMap = Record<string, number>;

/**
 * Convert an amount between two currencies using rates expressed relative to a
 * common base (as returned by GET /api/exchange-rates).
 *
 * Display-only. Never use this for cart, checkout, order or payment amounts.
 */
export function convert(
  amount: number,
  from: string,
  to: string,
  rates: RateMap,
): number | null {
  const fromRate = rates?.[from];
  const toRate = rates?.[to];

  if (!Number.isFinite(amount) || !fromRate || !toRate) {
    return null;
  }

  return (amount / fromRate) * toRate;
}

/**
 * Format a numeric amount as currency. Falls back to a plain `CODE 1,234.56`
 * string if the runtime doesn't recognise the currency code.
 */
export function formatCurrency(amount: number, currency: string): string {
  if (!Number.isFinite(amount)) {
    return "";
  }

  try {
    return new Intl.NumberFormat(undefined, {
      style: "currency",
      currency,
      // LBP has no minor unit; USD keeps cents.
      maximumFractionDigits: currency === "LBP" ? 0 : 2,
    }).format(amount);
  } catch {
    const rounded =
      currency === "LBP" ? Math.round(amount) : amount.toFixed(2);
    return `${currency} ${Number(rounded).toLocaleString()}`;
  }
}

const RELATIVE_UNITS: [Intl.RelativeTimeFormatUnit, number][] = [
  ["year", 60 * 60 * 24 * 365],
  ["month", 60 * 60 * 24 * 30],
  ["week", 60 * 60 * 24 * 7],
  ["day", 60 * 60 * 24],
  ["hour", 60 * 60],
  ["minute", 60],
];

/**
 * Parse an API timestamp into a Date.
 *
 * The backend emits UTC. If a value ever arrives without a timezone designator
 * (a bare `YYYY-MM-DDTHH:MM:SS`), `new Date()` would parse it in the browser's
 * local zone — so we append `Z` and force UTC. Values that already carry `Z` or
 * a `+hh:mm` / `-hh:mm` offset, and pure date strings, are left untouched.
 */
function parseApiTimestamp(iso: string): Date {
  if (typeof iso !== "string" || iso === "") {
    return new Date(NaN);
  }

  const hasZone = /([zZ])$|([+-]\d{2}:?\d{2})$/.test(iso);
  const normalized =
    hasZone || !iso.includes("T") ? iso : `${iso}Z`;

  return new Date(normalized);
}

/**
 * "3 hours ago" / "in 2 days" style relative time for an API timestamp.
 * Locale-aware via Intl.RelativeTimeFormat (no dependency); falls back to a
 * locale date string for anything older than ~1 week.
 */
export function formatRelativeTime(iso: string, locale?: string): string {
  const date = parseApiTimestamp(iso);
  const then = date.getTime();

  if (!Number.isFinite(then)) {
    return "";
  }

  const diffSeconds = (then - Date.now()) / 1000;
  const absSeconds = Math.abs(diffSeconds);

  let rtf: Intl.RelativeTimeFormat | null = null;
  try {
    rtf = new Intl.RelativeTimeFormat(locale, { numeric: "auto" });
  } catch {
    rtf = null;
  }

  // Just created (accounts for request + render latency).
  if (absSeconds < 10) {
    return rtf ? rtf.format(0, "second") : "just now";
  }

  // Older than ~1 week -> show an absolute date.
  if (absSeconds > RELATIVE_UNITS[2][1] || !rtf) {
    return date.toLocaleDateString(locale);
  }

  for (const [unit, secondsInUnit] of RELATIVE_UNITS) {
    if (absSeconds >= secondsInUnit) {
      return rtf.format(Math.round(diffSeconds / secondsInUnit), unit);
    }
  }

  return rtf.format(Math.round(diffSeconds), "second");
}
