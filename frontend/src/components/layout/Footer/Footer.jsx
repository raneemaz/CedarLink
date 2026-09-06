import { Link } from "react-router-dom";
import { useTranslation } from "react-i18next";

export default function Footer() {
  const { t } = useTranslation();

  return (
    <footer className="border-t border-line bg-paper-raised">
      <div className="mx-auto flex max-w-7xl flex-col gap-3 px-4 py-6 text-small text-ink-muted sm:flex-row sm:items-center sm:justify-between">
        <div>
          <p>© {new Date().getFullYear()} CedarLink</p>
          <p className="mt-1 text-micro">{t("footer.tagline")}</p>
        </div>

        <nav className="flex items-center gap-4">
          <Link to="/privacy-policy" className="hover:text-ink hover:underline">
            {t("footer.privacy")}
          </Link>
          <Link to="/terms" className="hover:text-ink hover:underline">
            {t("footer.terms")}
          </Link>
        </nav>
      </div>
    </footer>
  );
}
