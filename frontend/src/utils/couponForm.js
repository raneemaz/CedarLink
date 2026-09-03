// Form-state <-> API-payload mapping for the coupon form. Split out of
// CouponForm.jsx so that file exports only its component — mixing the two
// breaks React Fast Refresh.

const EMPTY = {
  code: "",
  discount_type: "percentage",
  value: "",
  min_order_total: "",
  starts_at: "",
  ends_at: "",
  usage_limit: "",
  per_user_limit: "",
  is_active: true,
};

/** "2026-09-30T14:05:00+00:00" -> "2026-09-30T14:05" for datetime-local. */
function toLocalInput(value) {
  if (!value) return "";
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) return "";
  const pad = (n) => String(n).padStart(2, "0");
  return (
    `${date.getFullYear()}-${pad(date.getMonth() + 1)}-` +
    `${pad(date.getDate())}T${pad(date.getHours())}:${pad(date.getMinutes())}`
  );
}

export function couponToForm(coupon) {
  if (!coupon) return { ...EMPTY };
  return {
    code: coupon.code ?? "",
    discount_type: coupon.discount_type ?? "percentage",
    value: coupon.value ?? "",
    min_order_total: coupon.min_order_total ?? "",
    starts_at: toLocalInput(coupon.starts_at),
    ends_at: toLocalInput(coupon.ends_at),
    usage_limit: coupon.usage_limit ?? "",
    per_user_limit: coupon.per_user_limit ?? "",
    is_active: coupon.is_active ?? true,
  };
}

/** Form state -> request body. Blank optional fields go as null, not "". */
export function formToPayload(form) {
  const optional = (value) => (value === "" ? null : value);

  return {
    code: form.code.trim(),
    discount_type: form.discount_type,
    value: Number(form.value),
    min_order_total:
      form.min_order_total === "" ? null : Number(form.min_order_total),
    // datetime-local has no zone; the browser's local time is what the
    // vendor meant, so send it as an instant rather than a wall clock.
    starts_at: form.starts_at
      ? new Date(form.starts_at).toISOString()
      : null,
    ends_at: form.ends_at ? new Date(form.ends_at).toISOString() : null,
    usage_limit: optional(form.usage_limit),
    per_user_limit: optional(form.per_user_limit),
    is_active: form.is_active,
  };
}
