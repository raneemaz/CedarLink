import { useEffect, useState } from "react";
import { NavLink, Outlet, Link } from "react-router-dom";
import {
  Store,
  Package,
  ClipboardList,
  ArrowLeft,
  AlertTriangle,
} from "lucide-react";

import api from "../../services/api";

const NAV_ITEMS = [
  { to: "/vendor/store", label: "Store", icon: Store },
  { to: "/vendor/products", label: "Products", icon: Package },
  { to: "/vendor/orders", label: "Orders", icon: ClipboardList },
];

function VendorLayout() {
  const [storeRemoved, setStoreRemoved] = useState(false);

  useEffect(() => {
    let cancelled = false;
    api
      .get("/vendor/store")
      .then((response) => {
        if (!cancelled && response.data.store?.deleted_at) {
          setStoreRemoved(true);
        }
      })
      .catch(() => {
        /* no store / not reachable — the pages handle their own states */
      });
    return () => {
      cancelled = true;
    };
  }, []);

  return (
    <div className="min-h-screen bg-gray-50">
      <div className="mx-auto flex max-w-6xl flex-col gap-8 px-6 py-10 lg:flex-row">
        <aside className="w-full shrink-0 lg:w-56">
          <p className="mb-4 px-3 text-xs font-semibold uppercase tracking-wide text-gray-400">
            Vendor Console
          </p>

          <nav className="space-y-1">
            {NAV_ITEMS.map(({ to, label, icon: Icon }) => (
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
                {label}
              </NavLink>
            ))}
          </nav>

          <Link
            to="/"
            className="mt-6 flex items-center gap-2 px-3 text-sm text-gray-500 hover:text-emerald-700"
          >
            <ArrowLeft size={16} />
            Back to CedarLink
          </Link>
        </aside>

        <main className="min-w-0 flex-1">
          {storeRemoved ? (
            <div className="rounded-2xl border border-red-200 bg-red-50 p-8 text-center">
              <AlertTriangle
                size={28}
                className="mx-auto text-red-500"
              />
              <h1 className="mt-3 text-xl font-semibold text-gray-900">
                This store was removed by an administrator
              </h1>
              <p className="mt-2 text-sm text-gray-600">
                Your products are no longer listed and you cannot take new
                orders. Orders already placed are unaffected. Contact
                support if you think this is a mistake.
              </p>
            </div>
          ) : (
            <Outlet />
          )}
        </main>
      </div>
    </div>
  );
}

export default VendorLayout;
