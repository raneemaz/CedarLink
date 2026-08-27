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
        <label className="font-medium text-gray-700">
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
          border-gray-300
          px-4
          py-3
          focus:border-green-600
          focus:ring-2
          focus:ring-green-200
          outline-none
          transition
        "
      />
    </div>
  );
}

export default Input;