import { useEffect, useState } from "react";
import { useTranslation } from "react-i18next";
import { toast } from "react-toastify";

import api from "../../services/api";

function StatCard({ label, value }) {
  return (
    <div className="rounded-xl border border-border bg-surface-raised p-5">
      <p className="text-xs font-semibold uppercase tracking-wide text-text-faint">
        {label}
      </p>
      <p className="mt-2 text-2xl font-bold text-text-primary">{value}</p>
    </div>
  );
}

function Section({ title, children }) {
  return (
    <section className="mt-8">
      <h2 className="mb-3 text-sm font-semibold uppercase tracking-wide text-text-faint">
        {title}
      </h2>
      {children}
    </section>
  );
}

function AdminOverview() {
  const { t } = useTranslation();
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
        toast.error(t("adminOverview.errLoad"));
      } finally {
        if (!cancelled) setLoading(false);
      }
    })();
    return () => {
      cancelled = true;
    };
  }, [t]);

  if (loading) {
    return <p className="text-sm text-text-muted">{t("adminOverview.loading")}</p>;
  }

  if (!reports) {
    return <p className="text-sm text-text-muted">{t("adminOverview.noData")}</p>;
  }

  const usersByRole = reports.users_by_role || {};
  const ordersByStatus = reports.orders_by_status || {};

  return (
    <div>
      <h1 className="text-3xl font-bold text-text-primary">{t("adminOverview.title")}</h1>

      <Section title={t("adminOverview.sectionUsers")}>
        <div className="grid gap-4 sm:grid-cols-3">
          <StatCard label={t("adminOverview.statCustomers")} value={usersByRole.customer || 0} />
          <StatCard label={t("adminOverview.statVendors")} value={usersByRole.vendor || 0} />
          <StatCard label={t("adminOverview.statAdmins")} value={usersByRole.admin || 0} />
        </div>
      </Section>

      <Section title={t("adminOverview.sectionStores")}>
        <div className="grid gap-4 sm:grid-cols-3">
          <StatCard label={t("adminOverview.statActive")} value={reports.stores.active} />
          <StatCard label={t("adminOverview.statInactive")} value={reports.stores.inactive} />
          <StatCard label={t("adminOverview.statRemoved")} value={reports.stores.removed} />
        </div>
      </Section>

      <Section title={t("adminOverview.sectionProducts")}>
        <div className="grid gap-4 sm:grid-cols-2">
          <StatCard label={t("adminOverview.statLive")} value={reports.products.live} />
          <StatCard label={t("adminOverview.statDeleted")} value={reports.products.deleted} />
        </div>
      </Section>

      <Section title={t("adminOverview.sectionOrders")}>
        <div className="grid gap-4 sm:grid-cols-3 lg:grid-cols-5">
          {["pending", "processing", "delivered", "canceled"].map(
            (status) => (
              <StatCard
                key={status}
                label={t(`orderStatus.${status}`)}
                value={ordersByStatus[status] || 0}
              />
            ),
          )}
          <StatCard
            label={t("adminOverview.statTotalValue")}
            value={`$${reports.total_order_value.toFixed(2)}`}
          />
        </div>
      </Section>

      <Section title={t("adminOverview.sectionTopStores")}>
        {reports.top_stores_by_orders.length === 0 ? (
          <p className="text-sm text-text-muted">{t("adminOverview.noOrders")}</p>
        ) : (
          <ol className="divide-y divide-border-subtle overflow-hidden rounded-xl border border-border bg-surface-raised">
            {reports.top_stores_by_orders.map((row, index) => (
              <li
                key={row.store}
                className="flex items-center justify-between px-5 py-3 text-sm"
              >
                <span className="text-text-emphasis">
                  {index + 1}. {row.store}
                </span>
                <span className="font-medium text-text-primary">
                  {t("adminOverview.orderCount", { count: row.order_count })}
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
