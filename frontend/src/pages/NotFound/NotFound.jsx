import { Link } from "react-router-dom";
import { useTranslation } from "react-i18next";

function NotFound() {
  const { t } = useTranslation();

  return (
    <div className="flex min-h-[70vh] flex-col items-center justify-center px-6 text-center">
      <p className="text-5xl font-bold text-emerald-700">404</p>
      <h1 className="mt-4 text-2xl font-semibold text-gray-900">
        {t("notFound.title")}
      </h1>
      <p className="mt-2 text-gray-500">{t("notFound.body")}</p>
      <Link
        to="/"
        className="mt-6 rounded-lg bg-emerald-700 px-5 py-2.5 text-sm font-semibold text-white transition hover:bg-emerald-800"
      >
        {t("notFound.backHome")}
      </Link>
    </div>
  );
}

export default NotFound;
