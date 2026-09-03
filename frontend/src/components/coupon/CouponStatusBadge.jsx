import { useTranslation } from "react-i18next";

import { STATUS_CLASSES, couponStatus } from "../../utils/coupon";

/** Scheduled / Active / Expired / Limit reached / Inactive. */
function CouponStatusBadge({ coupon }) {
  const { t } = useTranslation();
  const status = couponStatus(coupon);

  return (
    <span
      className={`inline-flex rounded-full px-2.5 py-0.5 text-xs font-semibold ${STATUS_CLASSES[status]}`}
    >
      {t(`coupon.status.${status}`)}
    </span>
  );
}

export default CouponStatusBadge;
