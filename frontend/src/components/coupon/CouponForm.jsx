import { useState } from "react";
import { useTranslation } from "react-i18next";

function Field({ label, hint, htmlFor, children }) {
  return (
    <div>
      <label
        htmlFor={htmlFor}
        className="mb-1.5 block text-sm font-medium text-slate-700"
      >
        {label}
      </label>
      {children}
      {hint && <p className="mt-1 text-xs text-slate-500">{hint}</p>}
    </div>
  );
}

const INPUT =
  "w-full rounded-lg border border-slate-300 px-3 py-2 text-sm outline-none " +
  "focus:border-emerald-600 focus:ring-1 focus:ring-emerald-600";

/**
 * Create / edit form, shared by the vendor and admin coupon pages.
 *
 * There is no scope control. A coupon's store is decided by the endpoint it
 * is posted to — the vendor routes take it from the URL and never from the
 * body — so offering a "platform-wide" switch here would be offering
 * something the vendor API will not honour. The admin page posts to the
 * admin endpoint, which is platform-wide by construction.
 */
function CouponForm({ form, setForm, onSubmit, onCancel, saving, editing }) {
  const { t } = useTranslation();
  const [touched, setTouched] = useState(false);

  const set = (name) => (event) => {
    const { value, type, checked } = event.target;
    setForm((prev) => ({
      ...prev,
      [name]: type === "checkbox" ? checked : value,
    }));
  };

  const isPercentage = form.discount_type === "percentage";

  const valueError = (() => {
    if (form.value === "") return t("coupon.form.errValueRequired");
    const numeric = Number(form.value);
    if (Number.isNaN(numeric)) return t("coupon.form.errValueNumber");
    if (isPercentage && (numeric < 1 || numeric > 100)) {
      return t("coupon.form.errPercentageRange");
    }
    if (!isPercentage && numeric <= 0) {
      return t("coupon.form.errFixedPositive");
    }
    return "";
  })();

  const codeError = form.code.trim() ? "" : t("coupon.form.errCodeRequired");

  const windowError =
    form.starts_at && form.ends_at && form.ends_at <= form.starts_at
      ? t("coupon.form.errWindow")
      : "";

  const invalid = Boolean(codeError || valueError || windowError);

  const submit = (event) => {
    event.preventDefault();
    setTouched(true);
    if (invalid) return;
    onSubmit();
  };

  const show = (message) => (touched && message ? message : "");

  return (
    <form onSubmit={submit} className="space-y-5">
      <div className="grid gap-5 sm:grid-cols-2">
        <Field
          htmlFor="coupon-form-code"
          label={t("coupon.form.code")}
          hint={t("coupon.form.codeHint")}
        >
          <input
            id="coupon-form-code"
            value={form.code}
            onChange={set("code")}
            dir="ltr"
            className={`${INPUT} uppercase`}
            placeholder="SUMMER20"
          />
          {show(codeError) && (
            <p className="mt-1 text-xs text-red-600">{codeError}</p>
          )}
        </Field>

        <Field
          htmlFor="coupon-form-type"
          label={t("coupon.form.discountType")}
        >
          <select
            id="coupon-form-type"
            value={form.discount_type}
            onChange={set("discount_type")}
            className={INPUT}
          >
            <option value="percentage">
              {t("coupon.form.typePercentage")}
            </option>
            <option value="fixed">{t("coupon.form.typeFixed")}</option>
          </select>
        </Field>

        <Field
          htmlFor="coupon-form-value"
          label={
            isPercentage
              ? t("coupon.form.valuePercentage")
              : t("coupon.form.valueFixed")
          }
          hint={
            isPercentage
              ? t("coupon.form.valuePercentageHint")
              : t("coupon.form.valueFixedHint")
          }
        >
          <input
            id="coupon-form-value"
            type="number"
            step={isPercentage ? "1" : "0.01"}
            min={isPercentage ? "1" : "0.01"}
            max={isPercentage ? "100" : undefined}
            value={form.value}
            onChange={set("value")}
            dir="ltr"
            className={INPUT}
          />
          {show(valueError) && (
            <p className="mt-1 text-xs text-red-600">{valueError}</p>
          )}
        </Field>

        <Field
          htmlFor="coupon-form-min"
          label={t("coupon.form.minOrderTotal")}
          hint={t("coupon.form.minOrderTotalHint")}
        >
          <input
            id="coupon-form-min"
            type="number"
            step="0.01"
            min="0"
            value={form.min_order_total}
            onChange={set("min_order_total")}
            dir="ltr"
            placeholder={t("coupon.form.noMinimum")}
            className={INPUT}
          />
        </Field>

        <Field htmlFor="coupon-form-starts" label={t("coupon.form.startsAt")}>
          <input
            id="coupon-form-starts"
            type="datetime-local"
            value={form.starts_at}
            onChange={set("starts_at")}
            dir="ltr"
            className={INPUT}
          />
        </Field>

        <Field
          htmlFor="coupon-form-ends"
          label={t("coupon.form.endsAt")}
          hint={t("coupon.form.windowHint")}
        >
          <input
            id="coupon-form-ends"
            type="datetime-local"
            value={form.ends_at}
            onChange={set("ends_at")}
            dir="ltr"
            className={INPUT}
          />
          {show(windowError) && (
            <p className="mt-1 text-xs text-red-600">{windowError}</p>
          )}
        </Field>

        {/* Both limits count *uses*, not people. An order spanning several
            stores becomes one order per store and redeems one use each
            (ADR 0021), so "customers" would be the wrong noun on either
            of these. */}
        <Field
          htmlFor="coupon-form-usage"
          label={t("coupon.form.usageLimit")}
          hint={t("coupon.form.usageLimitHint")}
        >
          <input
            id="coupon-form-usage"
            type="number"
            min="1"
            step="1"
            value={form.usage_limit}
            onChange={set("usage_limit")}
            dir="ltr"
            placeholder={t("coupon.form.unlimited")}
            className={INPUT}
          />
        </Field>

        <Field
          htmlFor="coupon-form-per-user"
          label={t("coupon.form.perUserLimit")}
          hint={t("coupon.form.perUserLimitHint")}
        >
          <input
            id="coupon-form-per-user"
            type="number"
            min="1"
            step="1"
            value={form.per_user_limit}
            onChange={set("per_user_limit")}
            dir="ltr"
            placeholder={t("coupon.form.unlimited")}
            className={INPUT}
          />
        </Field>
      </div>

      <label className="flex items-start gap-3 rounded-lg bg-slate-50 p-4">
        <input
          type="checkbox"
          checked={form.is_active}
          onChange={set("is_active")}
          className="mt-0.5 h-4 w-4 rounded border-slate-300 text-emerald-700 focus:ring-emerald-600"
        />
        <span>
          <span className="block text-sm font-medium text-slate-800">
            {t("coupon.form.isActive")}
          </span>
          <span className="mt-0.5 block text-xs text-slate-500">
            {t("coupon.form.isActiveHint")}
          </span>
        </span>
      </label>

      <div className="flex justify-end gap-3 border-t border-slate-100 pt-4">
        <button
          type="button"
          onClick={onCancel}
          disabled={saving}
          className="cursor-pointer rounded-lg border border-slate-300 px-4 py-2 text-sm font-medium text-slate-700 hover:bg-slate-50 disabled:opacity-50"
        >
          {t("common.cancel")}
        </button>

        <button
          type="submit"
          disabled={saving}
          className="cursor-pointer rounded-lg bg-emerald-700 px-4 py-2 text-sm font-semibold text-white hover:bg-emerald-800 disabled:cursor-not-allowed disabled:opacity-50"
        >
          {saving
            ? t("common.working")
            : editing
              ? t("coupon.form.saveChanges")
              : t("coupon.form.create")}
        </button>
      </div>
    </form>
  );
}

export default CouponForm;
