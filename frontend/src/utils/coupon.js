// Shared coupon presentation logic: status derivation, the i18n key for a
// rejection, and the directional wrappers for a value.
//
// The status is derived here rather than sent by the server because it is a
// view concern — the same row is "Scheduled" now and "Active" in an hour
// with no write in between.

/** Status of a coupon, most-blocking reason first. */
export function couponStatus(coupon, now = new Date()) {
  if (!coupon.is_active) return "inactive";

  if (coupon.starts_at && new Date(coupon.starts_at) > now) {
    return "scheduled";
  }

  if (coupon.ends_at && new Date(coupon.ends_at) <= now) {
    return "expired";
  }

  if (
    coupon.usage_limit != null &&
    Number(coupon.used_count) >= Number(coupon.usage_limit)
  ) {
    return "limitReached";
  }

  return "active";
}

export const STATUS_CLASSES = {
  active: "bg-cedar-tint text-cedar-strong",
  scheduled: "bg-info-subtle text-info",
  expired: "bg-control text-ink-body",
  limitReached: "bg-warning-tint text-warning",
  inactive: "bg-control text-ink-secondary",
};

// Every rejection the backend can return (coupon_service), mapped to its
// own message. The whole point of the per-reason codes is that the
// customer is told *why*, so there is deliberately no shared fallback
// phrasing here — an unrecognised code falls through to the server's own
// message rather than to "invalid coupon".
export const REJECTION_KEYS = {
  coupon_unknown: "coupon.errUnknown",
  coupon_inactive: "coupon.errInactive",
  coupon_not_started: "coupon.errNotStarted",
  coupon_expired: "coupon.errExpired",
  coupon_below_minimum: "coupon.errBelowMinimum",
  coupon_usage_limit: "coupon.errUsageLimit",
  coupon_user_limit: "coupon.errUserLimit",
  coupon_wrong_store: "coupon.errWrongStore",
  coupon_fixed_multi_store: "coupon.errFixedMultiStore",
};

/**
 * Turn an axios error from a coupon endpoint into a message.
 *
 * `t` is i18next's translator. Falls back to the server's English message,
 * never to a generic "invalid coupon" — if a new reason code appears
 * before its string does, the customer still learns something specific.
 */
export function rejectionMessage(t, error, fallbackKey = "coupon.errGeneric") {
  const data = error?.response?.data;
  const key = REJECTION_KEYS[data?.code];

  if (key) {
    // Only the minimum-order message needs a value interpolated; the rest
    // ignore the options object.
    return t(key, { amount: formatMoney(data?.min_order_total) });
  }

  return data?.error || data?.message || t(fallbackKey);
}

export function formatMoney(amount) {
  return `$${Number(amount || 0).toFixed(2)}`;
}

/**
 * A coupon's headline value: "20%" or "$5.00".
 *
 * Both are directional. Under `dir="rtl"` an unwrapped "20%" renders as
 * "%20" and "$5.00" as "5.00$", because the sign is a neutral character
 * that takes the paragraph direction. Callers must render the result
 * inside `dir="ltr"` — `CouponValue` does it for them.
 */
export function couponValueText(coupon) {
  return coupon.discount_type === "percentage"
    ? `${Number(coupon.value)}%`
    : formatMoney(coupon.value);
}
