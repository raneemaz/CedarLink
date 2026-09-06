function Input({
  label,
  type = "text",
  name,
  value,
  onChange,
  placeholder,
  required = false,
  autoComplete,
}) {
  return (
    <div className="flex flex-col gap-2 mb-5">
      {label && (
        <label className="font-medium text-ink-body">
          {label}
        </label>
      )}

      <input
        type={type}
        name={name}
        value={value}
        onChange={onChange}
        placeholder={placeholder}
        required={required}
        autoComplete={autoComplete}
        className="
          w-full
          rounded-xl
          border
          border-line-strong
          px-4
          py-3
          focus:border-cedar-ring
          focus:ring-2
          focus:ring-cedar-tint
          outline-none
          transition
        "
      />
    </div>
  );
}

export default Input;