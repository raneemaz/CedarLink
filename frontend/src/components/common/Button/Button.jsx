/**
 * The five button treatments from the redesign's component sheet.
 *
 * Pill radius and 13/24 padding are the sheet's, not a choice made here.
 * `secondary` is the sheet's outline treatment — the name is kept because
 * five call sites use it and this session does not move component
 * boundaries.
 *
 * Disabled is a variant of its own in the sheet rather than an opacity
 * wash: a 50%-opacity cedar fill on warm paper turns muddy green, where a
 * flat control fill reads as unavailable at any size.
 */
const VARIANTS = {
  primary: "bg-cedar text-on-cedar hover:bg-cedar-strong",

  // The sheet's .btn-outline: 1.5px cedar-strong edge, fills on hover.
  secondary:
    "border-[1.5px] border-cedar-strong text-cedar-strong " +
    "hover:bg-cedar-strong hover:text-on-cedar",

  ghost: "text-ink hover:bg-paper-sunken",

  danger: "bg-danger text-on-danger hover:bg-danger-strong",
};

function Button({
  children,
  type = "button",
  variant = "primary",
  onClick,
  disabled = false,
  className = "",
}) {
  return (
    <button
      type={type}
      onClick={onClick}
      disabled={disabled}
      className={`
        px-6 py-3
        rounded-pill
        text-small
        font-semibold
        transition
        duration-150
        focus-visible:outline focus-visible:outline-2
        focus-visible:outline-offset-2 focus-visible:outline-cedar-ring
        disabled:cursor-not-allowed
        disabled:border-transparent
        disabled:bg-control
        disabled:text-ink-disabled
        disabled:hover:bg-control
        ${disabled ? "" : VARIANTS[variant]}
        ${className}
      `}
    >
      {children}
    </button>
  );
}

export default Button;
