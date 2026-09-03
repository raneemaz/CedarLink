import { couponValueText } from "../../utils/coupon";

/**
 * A coupon's value — "20%" or "$5.00" — forced left-to-right.
 *
 * Both the percent sign and the currency symbol are directionally neutral,
 * so in an Arabic paragraph the bidi algorithm renders "20%" as "%20" and
 * "$5.00" as "5.00$". Money already gets this treatment in `Price`; this is
 * the same rule for the percentage case.
 */
function CouponValue({ coupon, className = "" }) {
  return (
    <span dir="ltr" className={className}>
      {couponValueText(coupon)}
    </span>
  );
}

export default CouponValue;
