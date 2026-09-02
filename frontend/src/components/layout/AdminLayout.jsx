import { NavLink, Outlet, Link } from "react-router-dom";
import { useTranslation } from "react-i18next";
import {
  LayoutDashboard,
  Users,
  Store,
  Tags,
  Star,
  ArrowLeft,
} from "lucide-react";

const NAV_ITEMS = [
  { to: "/admin/overview", key: "overview", icon: LayoutDashboard },
  { to: "/admin/users", key: "users", icon: Users },
  { to: "/admin/stores", key: "stores", icon: Store },
  { to: "/admin/categories", key: "categories", icon: Tags },
  { to: "/admin/reviews", key: "reviews", icon: Star },
];

function AdminLayout() {
  const { t } = useTranslation();

  return (
    <div className="min-h-screen bg-gray-50">
      <div className="mx-auto flex max-w-6xl flex-col gap-8 px-6 py-10 lg:flex-row">
        <aside className="w-full shrink-0 lg:w-56">
          <p className="mb-4 px-3 text-xs font-semibold uppercase tracking-wide text-gray-400">
            {t("adminLayout.console")}
          </p>

          <nav className="space-y-1">
            {NAV_ITEMS.map(({ to, key, icon: Icon }) => (
              <NavLink
                key={to}
                to={to}
                className={({ isActive }) =>
                  `flex items-center gap-3 rounded-lg px-3 py-2.5 text-sm transition ${
                    isActive
                      ? "bg-emerald-50 font-medium text-emerald-700"
                      : "text-gray-700 hover:bg-gray-100"
                  }`
                }
              >
                <Icon size={18} />
                {t(`adminLayout.${key}`)}
              </NavLink>
            ))}
          </nav>

          <Link
            to="/"
            className="mt-6 flex items-center gap-2 px-3 text-sm text-gray-500 hover:text-emerald-700"
          >
            <ArrowLeft size={16} className="rtl:rotate-180" />
            {t("common.backToCedarLink")}
          </Link>
        </aside>

        <main className="min-w-0 flex-1">
          <Outlet />
        </main>
      </div>
    </div>
  );
}

export default AdminLayout;
