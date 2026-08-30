// Shared helpers.

export type RateMap = Record<string, number>;

/**
 * Map a UI language to the locale used for Intl formatting.
 *
 * Arabic keeps its own month/day names and RTL number grouping but uses
 * Western digits (0-9), forced with the `-u-nu-latn` extension. Prices,
 * quantities and order numbers in Lebanese commerce are written in Western
 * digits, and mixing digit systems across the app would be worse than
 * either alone. See docs/decisions/0010-rtl-and-localized-formatting.md.
 */
export function formattingLocale(language?: string): string {
  switch (language) {
    case "ar":
      return "ar-u-nu-latn";
    case "fr":
      return "fr";
    default:
      return "en";
  }
}

/**
 * Format an API timestamp as a localized date (no time). `language` is the
 * UI language code (`en` | `ar` | `fr`), not a full locale.
 */
// A spelled-out month avoids the digit-order ambiguity a slash-separated
// numeric date picks up when it is reordered inside an RTL paragraph
// ("30/08/2026" flipping to "2026/08/30").
const DATE_OPTS: Intl.DateTimeFormatOptions = {
  day: "numeric",
  month: "long",
  year: "numeric",
};

export function formatDate(
  iso: string,
  language?: string,
  options: Intl.DateTimeFormatOptions = DATE_OPTS,
): string {
  const date = parseApiTimestamp(iso);
  if (!Number.isFinite(date.getTime())) {
    return "";
  }
  try {
    return new Intl.DateTimeFormat(
      formattingLocale(language),
      options,
    ).format(date);
  } catch {
    return date.toLocaleDateString();
  }
}

/**
 * Format an API timestamp as a localized date and time.
 */
export function formatDateTime(iso: string, language?: string): string {
  return formatDate(iso, language, {
    ...DATE_OPTS,
    hour: "2-digit",
    minute: "2-digit",
  });
}

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
export function formatCurrency(
  amount: number,
  currency: string,
  language?: string,
): string {
  if (!Number.isFinite(amount)) {
    return "";
  }

  try {
    return new Intl.NumberFormat(formattingLocale(language), {
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
 * localized date for anything older than ~1 week. `language` is the UI
 * language code (`en` | `ar` | `fr`).
 */
export function formatRelativeTime(iso: string, language?: string): string {
  const date = parseApiTimestamp(iso);
  const then = date.getTime();

  if (!Number.isFinite(then)) {
    return "";
  }

  const locale = formattingLocale(language);
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
    return formatDate(iso, language);
  }

  for (const [unit, secondsInUnit] of RELATIVE_UNITS) {
    if (absSeconds >= secondsInUnit) {
      return rtf.format(Math.round(diffSeconds / secondsInUnit), unit);
    }
  }

  return rtf.format(Math.round(diffSeconds), "second");
}
