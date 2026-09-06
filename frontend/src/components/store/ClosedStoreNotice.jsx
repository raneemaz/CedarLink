import { useTranslation } from "react-i18next";
import { Clock, Ban } from "lucide-react";

import { formatNextOpening } from "../../utils/storeStatus";

/**
 * What a shut store tells a customer.
 *
 * Two different messages, because being closed no longer means the same
 * thing everywhere (ADR 0025):
 *
 * - the store takes orders anyway → say when it opens and that delivery
 *   follows, so the customer knows the wait rather than guessing;
 * - it does not → the existing refusal.
 *
 * Renders nothing for an open store, so callers can drop it in without a
 * surrounding conditional.
 */
function ClosedStoreNotice({
  isOpen,
  acceptsOrders,
  nextOpeningTime,
  className = "",
}) {
  const { t, i18n } = useTranslation();

  if (isOpen !== false) return null;

  if (!acceptsOrders) {
    return (
      <p
        className={`flex items-start gap-2 rounded-control bg-warning-subtle px-3 py-2 text-small text-warning ${className}`}
      >
        <Ban size={16} className="mt-0.5 shrink-0" />
        {t("storeClosed.cannotOrder")}
      </p>
    );
  }

  const opening = formatNextOpening(nextOpeningTime, i18n.language);

  return (
    <p
      className={`flex items-start gap-2 rounded-control bg-info-subtle px-3 py-2 text-small text-info ${className}`}
    >
      <Clock size={16} className="mt-0.5 shrink-0" />
      {opening
        ? t("storeClosed.opensAt", { opening })
        : t("storeClosed.ordersWelcome")}
    </p>
  );
}

export default ClosedStoreNotice;
