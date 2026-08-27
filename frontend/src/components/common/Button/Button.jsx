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
      "bg-green-700 hover:bg-green-800 text-white",

    secondary:
      "bg-gray-200 hover:bg-gray-300 text-gray-800",

    danger:
      "bg-red-600 hover:bg-red-700 text-white",
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