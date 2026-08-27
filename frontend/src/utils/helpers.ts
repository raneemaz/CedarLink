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
