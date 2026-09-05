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
      "bg-brand hover:bg-brand-strong text-on-brand",

    secondary:
      "bg-control hover:bg-control-hover text-text-emphasis",

    danger:
      "bg-danger hover:bg-danger-strong text-on-brand",
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