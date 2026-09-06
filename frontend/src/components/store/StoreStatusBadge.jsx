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
      className={`inline-flex items-center gap-1.5 rounded-pill px-3.5 py-1.5 text-micro font-bold ${
        open
          ? "bg-cedar-tint text-cedar-strong"
          : "bg-paper-sunken text-ink-muted"
      } ${className}`}
    >
      <span
        className={`h-1.5 w-1.5 rounded-pill ${
          open ? "bg-cedar-ring" : "bg-ink-faint"
        }`}
      />
      {open ? t("storeOpenBadge.open") : t("storeOpenBadge.closed")}
    </span>
  );
}

export default StoreStatusBadge;
