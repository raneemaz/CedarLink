import { useEffect, useState } from "react";
import { toast } from "react-toastify";

import api from "../../services/api";

function StatCard({ label, value }) {
  return (
    <div className="rounded-xl border border-gray-200 bg-white p-5">
      <p className="text-xs font-semibold uppercase tracking-wide text-gray-400">
        {label}
      </p>
      <p className="mt-2 text-2xl font-bold text-gray-900">{value}</p>
    </div>
  );
}

function Section({ title, children }) {
  return (
    <section className="mt-8">
      <h2 className="mb-3 text-sm font-semibold uppercase tracking-wide text-gray-400">
        {title}
      </h2>
      {children}
    </section>
  );
}

function AdminOverview() {
  const [reports, setReports] = useState(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    let cancelled = false;
    (async () => {
      try {
        const response = await api.get("/admin/reports");
        if (!cancelled) setReports(response.data);
      } catch (error) {
        if (cancelled) return;
        console.error("Failed to load reports:", error);
        toast.error("Unable to load the overview.");
      } finally {
        if (!cancelled) setLoading(false);
      }
    })();
    return () => {
      cancelled = true;
    };
  }, []);

  if (loading) {
    return <p className="text-sm text-gray-500">Loading overview...</p>;
  }

  if (!reports) {
    return <p className="text-sm text-gray-500">No data.</p>;
  }

  const usersByRole = reports.users_by_role || {};
  const ordersByStatus = reports.orders_by_status || {};

  return (
    <div>
      <h1 className="text-3xl font-bold text-gray-900">Overview</h1>

      <Section title="Users">
        <div className="grid gap-4 sm:grid-cols-3">
          <StatCard label="Customers" value={usersByRole.customer || 0} />
          <StatCard label="Vendors" value={usersByRole.vendor || 0} />
          <StatCard label="Admins" value={usersByRole.admin || 0} />
        </div>
      </Section>

      <Section title="Stores">
        <div className="grid gap-4 sm:grid-cols-3">
          <StatCard label="Active" value={reports.stores.active} />
          <StatCard label="Inactive" value={reports.stores.inactive} />
          <StatCard label="Removed" value={reports.stores.removed} />
        </div>
      </Section>

      <Section title="Products">
        <div className="grid gap-4 sm:grid-cols-2">
          <StatCard label="Live" value={reports.products.live} />
          <StatCard label="Deleted" value={reports.products.deleted} />
        </div>
      </Section>

      <Section title="Orders">
        <div className="grid gap-4 sm:grid-cols-3 lg:grid-cols-5">
          {["pending", "processing", "delivered", "canceled"].map(
            (status) => (
              <StatCard
                key={status}
                label={status}
                value={ordersByStatus[status] || 0}
              />
            ),
          )}
          <StatCard
            label="Total value"
            value={`$${reports.total_order_value.toFixed(2)}`}
          />
        </div>
      </Section>

      <Section title="Top stores by orders">
        {reports.top_stores_by_orders.length === 0 ? (
          <p className="text-sm text-gray-500">No orders yet.</p>
        ) : (
          <ol className="divide-y divide-gray-100 overflow-hidden rounded-xl border border-gray-200 bg-white">
            {reports.top_stores_by_orders.map((row, index) => (
              <li
                key={row.store}
                className="flex items-center justify-between px-5 py-3 text-sm"
              >
                <span className="text-gray-800">
                  {index + 1}. {row.store}
                </span>
                <span className="font-medium text-gray-900">
                  {row.order_count}{" "}
                  {row.order_count === 1 ? "order" : "orders"}
                </span>
              </li>
            ))}
          </ol>
        )}
      </Section>
    </div>
  );
}

export default AdminOverview;
