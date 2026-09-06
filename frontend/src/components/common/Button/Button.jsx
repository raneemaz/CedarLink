function Button({
  children,
  type = "button",
  variant = "primary",
  onClick,
  disabled = false,
  className = "",
}) {
  const variants = {
    primary:
      "bg-cedar hover:bg-cedar-strong text-on-cedar",

    secondary:
      "bg-control hover:bg-control-hover text-ink-emphasis",

    danger:
      "bg-danger hover:bg-danger-strong text-on-danger",
  };

  return (
    <button
      type={type}
      onClick={onClick}
      disabled={disabled}
      className={`
        px-4 py-3
        rounded-xl
        font-semibold
        transition
        duration-200
        disabled:opacity-50
        disabled:cursor-not-allowed
        ${variants[variant]}
        ${className}
      `}
    >
      {children}
    </button>
  );
}

export default Button;