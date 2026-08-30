import { useCurrency } from "../../context/CurrencyContext";

/**
 * Browsing-surface price display.
 *
 * Always shows the authoritative base-currency amount (USD). When the user has
 * chosen a different display currency, an approximate converted amount is shown
 * beneath it, visually secondary so it can never be mistaken for the amount
 * that will actually be charged (cart / checkout / orders / payments stay USD).
 */
function Price({ amount, from = "USD", className = "", approxClassName = "" }) {
  const { isConverted, formatBase, formatConverted } = useCurrency();

  const base = formatBase(amount, from);
  const converted = isConverted ? formatConverted(amount, from) : null;

  return (
    <span className={`inline-flex flex-col leading-tight ${className}`}>
      {/* Money reads left-to-right even in an RTL page — otherwise the
          currency symbol and digits get reordered ("$US 3.50"). */}
      <span dir="ltr">{base}</span>

      {converted && (
        <span
          dir="ltr"
          className={`text-xs font-normal text-gray-400 ${approxClassName}`}
          title="Approximate — you are charged in USD"
        >
          ≈ {converted}
        </span>
      )}
    </span>
  );
}

export default Price;
