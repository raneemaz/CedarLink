import { useState } from "react";
import { useTranslation } from "react-i18next";
import { toast } from "react-toastify";
import { AlertTriangle } from "lucide-react";

import api from "../../services/api";
import Toggle from "../../components/common/Toggle/Toggle";
import { Section } from "./VendorStore";

/**
 * "Take orders while closed" for the vendor store page.
 *
 * Deliberately its own labelled section rather than a checkbox among the
 * delivery settings: the vendor is deciding whether a sale outside
 * opening hours is captured or refused, and the answer differs by trade —
 * right for a clothes shop, wrong for anything perishable.
 *
 * The override caveat is stated on the control itself, not buried in
 * documentation, because it is the one thing that would otherwise
 * surprise a vendor who set both. See ADR 0025.
 */
function StoreClosedOrdersPanel({ store, onStoreChange }) {
  const { t } = useTranslation();
  const [saving, setSaving] = useState(false);

  const enabled = Boolean(store.accepts_orders_when_closed);

  const save = async (next) => {
    setSaving(true);
    try {
      const { data } = await api.put(`/stores/${store.id}`, {
        accepts_orders_when_closed: next,
      });
      onStoreChange(data.store);
      toast.success(
        next
          ? t("vendorStore.closedOrders.toastOn")
          : t("vendorStore.closedOrders.toastOff"),
      );
    } catch (error) {
      console.error("Failed to save closed-order setting:", error);
      toast.error(
        error.response?.data?.message ||
          t("vendorStore.closedOrders.errSave"),
      );
    } finally {
      setSaving(false);
    }
  };

  return (
    <Section
      title={t("vendorStore.closedOrders.title")}
      description={t("vendorStore.closedOrders.description")}
    >
      <div className="space-y-4">
        <Toggle
          checked={enabled}
          disabled={saving}
          onChange={save}
          label={t("vendorStore.closedOrders.label")}
          description={
            enabled
              ? t("vendorStore.closedOrders.onDesc")
              : t("vendorStore.closedOrders.offDesc")
          }
        />

        <div className="flex items-start gap-3 rounded-control border border-warning-border bg-warning-subtle p-4">
          <AlertTriangle
            size={18}
            className="mt-0.5 shrink-0 text-warning-muted"
          />
          <p className="text-small text-warning">
            {t("vendorStore.closedOrders.overrideNote")}
          </p>
        </div>
      </div>
    </Section>
  );
}

export default StoreClosedOrdersPanel;
