import { ToastContainer } from "react-toastify";
import { useTranslation } from "react-i18next";

import { isRtl } from "../../i18n/i18n";

/**
 * ToastContainer that follows the document direction — toasts slide in from
 * the trailing edge and stack on the correct side in Arabic.
 */
export default function AppToaster() {
  const { i18n } = useTranslation();
  const rtl = isRtl(i18n.language);

  return (
    <ToastContainer
      position={rtl ? "top-left" : "top-right"}
      rtl={rtl}
      autoClose={3000}
    />
  );
}
