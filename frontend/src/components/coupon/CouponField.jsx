import { useState } from "react";
import { useTranslation } from "react-i18next";
import { Tag, X } from "lucide-react";

import api from "../../services/api";
import { rejectionMessage } from "../../utils/coupon";

/**
 * Code entry for the cart and checkout summaries.
 *
 * The applied code shows as a removable chip so clearing it is one obvious
 * press rather than a hunt. Applying calls the validation endpoint — which
 * redeems nothing — and on refusal shows the *specific* reason the backend
 * gave. There is no generic "invalid coupon" path: every rejection code has
 * its own string, and an unmapped one falls through to the server's message
 * rather than to a shrug.
 *
 * `onChanged` fires after a successful apply or clear so the parent can
 * re-fetch its pricing. The coupon lives on the cart server-side, so the
 * parent does not have to thread the code through anything.
 */
function CouponField({ appliedCode, onChanged, disabled }) {
  const { t } = useTranslation();

  const [code, setCode] = useState("");
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");

  const apply = async () => {
    const trimmed = code.trim();

    if (!trimmed) {
      setError(t("coupon.errEmpty"));
      return;
    }

    setBusy(true);
    setError("");

    try {
      // No delivery city: a discount only ever touches the goods, so a
      // code can be applied from the cart before one is chosen.
      await api.post("/cart/coupon", { code: trimmed });
      setCode("");
      onChanged?.();
    } catch (err) {
      setError(rejectionMessage(t, err));
    } finally {
      setBusy(false);
    }
  };

  const clear = async () => {
    setBusy(true);
    setError("");

    try {
      await api.delete("/cart/coupon");
      onChanged?.();
    } catch {
      setError(t("coupon.errClear"));
    } finally {
      setBusy(false);
    }
  };

  if (appliedCode) {
    return (
      <div>
        <span className="inline-flex items-center gap-2 rounded-full bg-brand-subtle py-1 ps-3 pe-1 text-sm font-medium text-brand-strong">
          <Tag size={14} />
          {/* A code is an identifier, not prose: it reads left-to-right
              even on an Arabic page. */}
          <span dir="ltr">{appliedCode}</span>
          <button
            type="button"
            onClick={clear}
            disabled={busy || disabled}
            aria-label={t("coupon.removeAria", { code: appliedCode })}
            className="cursor-pointer rounded-full p-1 text-brand transition hover:bg-brand-tint disabled:cursor-not-allowed disabled:opacity-50"
          >
            <X size={14} />
          </button>
        </span>

        {error && <p className="mt-2 text-sm text-danger">{error}</p>}
      </div>
    );
  }

  return (
    <div>
      <label
        htmlFor="coupon-code"
        className="mb-2 block text-sm text-text-secondary"
      >
        {t("coupon.fieldLabel")}
      </label>

      <div className="flex gap-2">
        <input
          id="coupon-code"
          type="text"
          value={code}
          onChange={(event) => {
            setCode(event.target.value);
            if (error) setError("");
          }}
          onKeyDown={(event) => {
            if (event.key === "Enter") {
              event.preventDefault();
              apply();
            }
          }}
          dir="ltr"
          placeholder={t("coupon.placeholder")}
          disabled={busy || disabled}
          className="min-w-0 flex-1 rounded-lg border border-border-strong px-3 py-2 text-sm uppercase outline-none focus:border-brand-ring focus:ring-1 focus:ring-brand-ring disabled:bg-surface"
        />

        <button
          type="button"
          onClick={apply}
          disabled={busy || disabled}
          className="shrink-0 cursor-pointer rounded-lg border border-brand px-4 py-2 text-sm font-semibold text-brand transition hover:bg-brand-subtle disabled:cursor-not-allowed disabled:opacity-50"
        >
          {busy ? t("coupon.applying") : t("coupon.apply")}
        </button>
      </div>

      {error && <p className="mt-2 text-sm text-danger">{error}</p>}
    </div>
  );
}

export default CouponField;
