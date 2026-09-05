/**
 * Controlled on/off switch used by the notification preferences page.
 */
function Toggle({ checked, onChange, label, description, disabled = false }) {
  return (
    <div className="flex items-center justify-between gap-4 py-4">
      <div className="min-w-0">
        <p className="font-medium text-text-primary">{label}</p>

        {description && (
          <p className="mt-1 text-sm text-text-muted">{description}</p>
        )}
      </div>

      <button
        type="button"
        role="switch"
        aria-checked={checked}
        aria-label={label}
        disabled={disabled}
        onClick={() => onChange(!checked)}
        className={`relative inline-flex h-6 w-11 shrink-0 cursor-pointer items-center rounded-full transition disabled:cursor-not-allowed disabled:opacity-60 ${
          checked ? "bg-brand" : "bg-control-hover"
        }`}
      >
        <span
          className={`inline-block h-5 w-5 transform rounded-full bg-surface-raised shadow transition ${
            checked ? "translate-x-5" : "translate-x-1"
          }`}
        />
      </button>
    </div>
  );
}

export default Toggle;
