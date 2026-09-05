import { useEffect, useState } from "react";
import { NavLink, Outlet, Link } from "react-router-dom";
import { useTranslation } from "react-i18next";
import {
  LayoutDashboard,
  Store,
  Package,
  ClipboardList,
  TicketPercent,
  ArrowLeft,
  AlertTriangle,
} from "lucide-react";

import api from "../../services/api";

const NAV_ITEMS = [
  { to: "/vendor/dashboard", key: "dashboard", icon: LayoutDashboard },
  { to: "/vendor/store", key: "store", icon: Store },
  { to: "/vendor/products", key: "products", icon: Package },
  { to: "/vendor/orders", key: "orders", icon: ClipboardList },
  { to: "/vendor/coupons", key: "coupons", icon: TicketPercent },
];

function VendorLayout() {
  const { t } = useTranslation();
  const [store, setStore] = useState(null);

  useEffect(() => {
    let cancelled = false;

    const refresh = () => {
      api
        .get("/vendor/store")
        .then((response) => {
          if (!cancelled) setStore(response.data.store);
        })
        .catch(() => {
          /* no store yet — the pages handle their own states */
        });
    };

    refresh();
    window.addEventListener("vendorStoreChanged", refresh);
    return () => {
      cancelled = true;
      window.removeEventListener("vendorStoreChanged", refresh);
    };
  }, []);

  const storeRemoved = Boolean(store?.deleted_at);
  const pendingApproval =
    store && !store.deleted_at && store.approval_status === "pending";
  const rejected =
    store && !store.deleted_at && store.approval_status === "rejected";

  return (
    <div className="min-h-screen bg-surface">
      <div className="mx-auto flex max-w-6xl flex-col gap-8 px-6 py-10 lg:flex-row">
        <aside className="w-full shrink-0 lg:w-56">
          <p className="mb-4 px-3 text-xs font-semibold uppercase tracking-wide text-text-faint">
            {t("vendorLayout.console")}
          </p>

          <nav className="space-y-1">
            {NAV_ITEMS.map(({ to, key, icon: Icon }) => (
              <NavLink
                key={to}
                to={to}
                className={({ isActive }) =>
                  `flex items-center gap-3 rounded-lg px-3 py-2.5 text-sm transition ${
                    isActive
                      ? "bg-brand-subtle font-medium text-brand"
                      : "text-text-body hover:bg-surface-sunken"
                  }`
                }
              >
                <Icon size={18} />
                {t(`vendorLayout.${key}`)}
              </NavLink>
            ))}
          </nav>

          <Link
            to="/"
            className="mt-6 flex items-center gap-2 px-3 text-sm text-text-muted hover:text-brand"
          >
            <ArrowLeft size={16} className="rtl:rotate-180" />
            {t("common.backToCedarLink")}
          </Link>
        </aside>

        <main className="min-w-0 flex-1">
          {storeRemoved ? (
            <div className="rounded-2xl border border-danger-border bg-danger-subtle p-8 text-center">
              <AlertTriangle
                size={28}
                className="mx-auto text-danger-accent"
              />
              <h1 className="mt-3 text-xl font-semibold text-text-primary">
                {t("vendorLayout.removedTitle")}
              </h1>
              <p className="mt-2 text-sm text-text-secondary">
                {t("vendorLayout.removedBody")}
              </p>
            </div>
          ) : (
            <>
              {pendingApproval && (
                <div className="mb-6 flex items-start gap-3 rounded-xl border border-warning-border bg-warning-subtle p-4">
                  <AlertTriangle
                    size={20}
                    className="mt-0.5 shrink-0 text-warning-accent"
                  />
                  <p className="text-sm text-warning">
                    <span className="font-semibold">
                      {t("vendorLayout.pendingTitle")}
                    </span>{" "}
                    {t("vendorLayout.pendingBody")}
                  </p>
                </div>
              )}

              {rejected && (
                <div className="mb-6 flex items-start gap-3 rounded-xl border border-danger-border bg-danger-subtle p-4">
                  <AlertTriangle
                    size={20}
                    className="mt-0.5 shrink-0 text-danger-accent"
                  />
                  <p className="text-sm text-danger-strong">
                    <span className="font-semibold">
                      {t("vendorLayout.rejectedTitle")}
                    </span>{" "}
                    {store?.approval_note ||
                      t("vendorLayout.rejectedBodyDefault")}
                  </p>
                </div>
              )}

              <Outlet />
            </>
          )}
        </main>
      </div>
    </div>
  );
}

export default VendorLayout;
