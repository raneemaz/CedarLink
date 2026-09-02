import { useTranslation } from "react-i18next";

/**
 * Open / closed pill for a store. Reads the server-computed `is_open_now`
 * (never recomputed on the client — see ADR 0013).
 */
function StoreStatusBadge({ store, className = "" }) {
  const { t } = useTranslation();
  const open = Boolean(store?.is_open_now);

  return (
    <span
      className={`inline-flex items-center gap-1.5 rounded-full px-2.5 py-0.5 text-xs font-semibold ${
        open
          ? "bg-emerald-100 text-emerald-800"
          : "bg-red-100 text-red-700"
      } ${className}`}
    >
      <span
        className={`h-1.5 w-1.5 rounded-full ${
          open ? "bg-emerald-600" : "bg-red-500"
        }`}
      />
      {open ? t("storeOpenBadge.open") : t("storeOpenBadge.closed")}
    </span>
  );
}

export default StoreStatusBadge;
