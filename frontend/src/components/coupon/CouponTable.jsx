import { useTranslation } from "react-i18next";
import { Pencil, Trash2 } from "lucide-react";

import CouponStatusBadge from "./CouponStatusBadge";
import CouponValue from "./CouponValue";
import { formatMoney } from "../../utils/coupon";

/**
 * The coupon list, shared by the vendor and admin pages.
 *
 * `onEdit` / `onDelete` are omitted for the admin's read-only view of other
 * stores' coupons — an administrator can see what is live across the
 * marketplace without being handed the vendor's controls.
 */
function CouponTable({ coupons, onEdit, onDelete, showStore = false }) {
  const { t, i18n } = useTranslation();

  const readOnly = !onEdit && !onDelete;

  const formatDate = (value) =>
    value
      ? new Date(value).toLocaleDateString(i18n.language, {
          day: "numeric",
          month: "short",
          year: "numeric",
        })
      : null;

  const windowText = (coupon) => {
    const from = formatDate(coupon.starts_at);
    const to = formatDate(coupon.ends_at);
    if (from && to) return t("coupon.windowBoth", { from, to });
    if (from) return t("coupon.windowFrom", { from });
    if (to) return t("coupon.windowUntil", { to });
    return t("coupon.windowAlways");
  };

  return (
    <div className="overflow-x-auto rounded-2xl border border-slate-200 bg-white">
      <table className="w-full min-w-[46rem] text-sm">
        <thead className="border-b border-slate-200 bg-slate-50 text-start">
          <tr>
            <th className="px-4 py-3 text-start font-semibold text-slate-600">
              {t("coupon.table.code")}
            </th>
            {showStore && (
              <th className="px-4 py-3 text-start font-semibold text-slate-600">
                {t("coupon.table.store")}
              </th>
            )}
            <th className="px-4 py-3 text-start font-semibold text-slate-600">
              {t("coupon.table.discount")}
            </th>
            <th className="px-4 py-3 text-start font-semibold text-slate-600">
              {t("coupon.table.minimum")}
            </th>
            <th className="px-4 py-3 text-start font-semibold text-slate-600">
              {t("coupon.table.window")}
            </th>
            <th className="px-4 py-3 text-start font-semibold text-slate-600">
              {t("coupon.table.used")}
            </th>
            <th className="px-4 py-3 text-start font-semibold text-slate-600">
              {t("coupon.table.status")}
            </th>
            {!readOnly && <th className="px-4 py-3" />}
          </tr>
        </thead>

        <tbody className="divide-y divide-slate-100">
          {coupons.map((coupon) => (
            <tr key={coupon.id} className="hover:bg-slate-50">
              <td className="px-4 py-3 font-mono font-medium text-slate-900">
                <span dir="ltr">{coupon.code}</span>
              </td>

              {showStore && (
                <td className="px-4 py-3 text-slate-600">
                  {coupon.store_name || t("coupon.platformWide")}
                </td>
              )}

              <td className="px-4 py-3 font-medium text-slate-800">
                <CouponValue coupon={coupon} />
              </td>

              <td className="px-4 py-3 text-slate-600">
                {coupon.min_order_total == null ? (
                  <span className="text-slate-400">—</span>
                ) : (
                  <span dir="ltr">{formatMoney(coupon.min_order_total)}</span>
                )}
              </td>

              <td className="px-4 py-3 text-slate-600">
                {windowText(coupon)}
              </td>

              <td className="px-4 py-3 text-slate-600">
                {coupon.usage_limit == null
                  ? t("coupon.usedUnlimited", {
                      count: Number(coupon.used_count),
                    })
                  : t("coupon.usedOfLimit", {
                      count: Number(coupon.usage_limit),
                      used: Number(coupon.used_count),
                      limit: Number(coupon.usage_limit),
                    })}
              </td>

              <td className="px-4 py-3">
                <CouponStatusBadge coupon={coupon} />
              </td>

              {!readOnly && (
                <td className="px-4 py-3">
                  <div className="flex items-center justify-end gap-1">
                    {onEdit && (
                      <button
                        type="button"
                        onClick={() => onEdit(coupon)}
                        aria-label={t("coupon.editAria", {
                          code: coupon.code,
                        })}
                        className="cursor-pointer rounded-lg p-2 text-slate-500 transition hover:bg-slate-100 hover:text-emerald-700"
                      >
                        <Pencil size={16} />
                      </button>
                    )}
                    {onDelete && (
                      <button
                        type="button"
                        onClick={() => onDelete(coupon)}
                        aria-label={t("coupon.deleteAria", {
                          code: coupon.code,
                        })}
                        className="cursor-pointer rounded-lg p-2 text-slate-500 transition hover:bg-red-50 hover:text-red-600"
                      >
                        <Trash2 size={16} />
                      </button>
                    )}
                  </div>
                </td>
              )}
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}

export default CouponTable;
