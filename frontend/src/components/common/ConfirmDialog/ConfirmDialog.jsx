import { useTranslation } from "react-i18next";

import Button from "../Button/Button";

/**
 * In-app confirmation dialog. Unlike window.confirm it does not block the
 * page or the JS event loop.
 */
function ConfirmDialog({
  open,
  title,
  message,
  confirmLabel,
  cancelLabel,
  variant = "danger",
  loading = false,
  onConfirm,
  onCancel,
  children,
}) {
  const { t } = useTranslation();

  if (!open) return null;

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/40 px-4">
      <div className="w-full max-w-md rounded-2xl bg-white p-6 shadow-xl">
        <h2 className="text-lg font-semibold text-gray-900">{title}</h2>

        {message && (
          <p className="mt-2 text-sm text-gray-600">{message}</p>
        )}

        {children && <div className="mt-4">{children}</div>}

        <div className="mt-6 flex justify-end gap-3">
          <Button
            variant="secondary"
            onClick={onCancel}
            disabled={loading}
          >
            {cancelLabel || t("confirmDialog.cancel")}
          </Button>

          <Button
            variant={variant}
            onClick={onConfirm}
            disabled={loading}
          >
            {loading
              ? t("confirmDialog.working")
              : confirmLabel || t("confirmDialog.confirm")}
          </Button>
        </div>
      </div>
    </div>
  );
}

export default ConfirmDialog;
