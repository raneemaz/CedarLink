import { useEffect, useMemo, useState } from "react";
import { useTranslation } from "react-i18next";
import { toast } from "react-toastify";

import api from "../../services/api";
import ConfirmDialog from "../../components/common/ConfirmDialog/ConfirmDialog";

const STATUS_BADGE = {
  pending: "bg-info-subtle text-info",
  active: "bg-success-subtle text-success",
  inactive: "bg-warning-tint text-warning-muted",
  rejected: "bg-danger-tint text-danger-strong",
  removed: "bg-control text-ink-secondary",
};

const DIALOG = {
  approve: {
    titleKey: "adminStores.approveTitle",
    confirmKey: "adminStores.approveConfirm",
    messageKey: "adminStores.approveMessage",
    variant: "primary",
  },
  reject: {
    titleKey: "adminStores.rejectTitle",
    confirmKey: "adminStores.rejectConfirm",
    messageKey: "adminStores.rejectMessage",
    variant: "danger",
  },
  remove: {
    titleKey: "adminStores.removeTitle",
    confirmKey: "adminStores.removeConfirm",
    messageKey: "adminStores.removeMessage",
    variant: "danger",
  },
};

function AdminStores() {
  const { t } = useTranslation();
  const [stores, setStores] = useState([]);
  const [loading, setLoading] = useState(true);
  const [filter, setFilter] = useState("all");

  const [action, setAction] = useState(null); // { store, type }
  const [note, setNote] = useState("");
  const [working, setWorking] = useState(false);

  const load = async () => {
    const response = await api.get("/admin/stores");
    setStores(response.data || []);
  };

  useEffect(() => {
    let cancelled = false;
    (async () => {
      try {
        await load();
      } catch (error) {
        if (!cancelled) {
          console.error("Failed to load stores:", error);
          toast.error(t("adminStores.errLoad"));
        }
      } finally {
        if (!cancelled) setLoading(false);
      }
    })();
    return () => {
      cancelled = true;
    };
  }, [t]);

  const pendingCount = useMemo(
    () => stores.filter((store) => store.status === "pending").length,
    [stores],
  );

  const visible = useMemo(
    () =>
      filter === "pending"
        ? stores.filter((store) => store.status === "pending")
        : stores,
    [stores, filter],
  );

  const open = (store, type) => {
    setNote("");
    setAction({ store, type });
  };

  const runAction = async () => {
    if (!action) return;
    const { store, type } = action;
    setWorking(true);
    try {
      if (type === "remove") {
        await api.delete(`/admin/stores/${store.id}`);
        toast.success(t("adminStores.toastRemoved", { name: store.name }));
      } else {
        await api.patch(`/admin/stores/${store.id}/${type}`, {
          note: note.trim(),
        });
        toast.success(
          type === "approve"
            ? t("adminStores.toastApproved", { name: store.name })
            : t("adminStores.toastRejected", { name: store.name }),
        );
      }
      await load();
      setAction(null);
    } catch (error) {
      console.error("Store action failed:", error);
      toast.error(
        error.response?.data?.error || t("adminStores.errAction"),
      );
    } finally {
      setWorking(false);
    }
  };

  if (loading) {
    return <p className="text-small text-ink-muted">{t("adminStores.loading")}</p>;
  }

  const dialogConfig = action ? DIALOG[action.type] : null;

  return (
    <div>
      <h1 className="mb-6 text-title font-bold text-ink">{t("adminStores.title")}</h1>

      <div className="mb-4 flex gap-2">
        {[
          { key: "all", label: t("adminStores.filterAll") },
          {
            key: "pending",
            label: t("adminStores.filterPending", { count: pendingCount }),
          },
        ].map(({ key, label }) => (
          <button
            key={key}
            type="button"
            onClick={() => setFilter(key)}
            className={`rounded-pill px-4 py-1.5 text-small font-medium transition ${
              filter === key
                ? "bg-cedar text-on-cedar"
                : "bg-paper-raised text-ink-secondary shadow-card hover:bg-paper"
            }`}
          >
            {label}
          </button>
        ))}
      </div>

      <div className="overflow-x-auto rounded-card bg-paper-raised shadow-card">
        <table className="min-w-full text-small">
          <thead>
            <tr className="border-b border-line-subtle text-start text-micro uppercase tracking-wide text-ink-faint">
              <th className="px-4 py-3 font-medium">{t("adminStores.colStore")}</th>
              <th className="px-4 py-3 font-medium">{t("adminStores.colOwner")}</th>
              <th className="px-4 py-3 font-medium">{t("adminStores.colProducts")}</th>
              <th className="px-4 py-3 font-medium">{t("adminStores.colStatus")}</th>
              <th className="px-4 py-3 font-medium text-end">{t("adminStores.colActions")}</th>
            </tr>
          </thead>
          <tbody className="divide-y divide-line-subtle">
            {visible.map((store) => (
              <tr key={store.id}>
                <td className="px-4 py-3">
                  <p className="font-medium text-ink">{store.name}</p>
                  <p className="text-ink-muted">{store.location || "—"}</p>
                  {store.approval_note && (
                    <p className="mt-1 text-micro text-ink-faint">
                      {t("adminStores.notePrefix", { note: store.approval_note })}
                    </p>
                  )}
                </td>
                <td className="px-4 py-3 text-ink-secondary">
                  <p>{store.owner_name || "—"}</p>
                  <p className="text-ink-faint">{store.owner_email}</p>
                </td>
                <td className="px-4 py-3 text-ink">
                  {store.product_count}
                </td>
                <td className="px-4 py-3">
                  <span
                    className={`rounded-pill px-2.5 py-1 text-micro font-semibold ${
                      STATUS_BADGE[store.status] || STATUS_BADGE.active
                    }`}
                  >
                    {t(`storeStatus.${store.status}`)}
                  </span>
                </td>
                <td className="px-4 py-3">
                  <div className="flex justify-end gap-4">
                    {store.status === "removed" ? (
                      <span className="text-micro text-ink-faint">—</span>
                    ) : (
                      <>
                        {(store.status === "pending" ||
                          store.status === "rejected") && (
                          <button
                            type="button"
                            onClick={() => open(store, "approve")}
                            className="font-medium text-cedar hover:underline"
                          >
                            {t("adminStores.approve")}
                          </button>
                        )}
                        {store.status === "pending" && (
                          <button
                            type="button"
                            onClick={() => open(store, "reject")}
                            className="font-medium text-warning-muted hover:underline"
                          >
                            {t("adminStores.reject")}
                          </button>
                        )}
                        <button
                          type="button"
                          onClick={() => open(store, "remove")}
                          className="font-medium text-danger hover:underline"
                        >
                          {t("adminStores.remove")}
                        </button>
                      </>
                    )}
                  </div>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>

      <ConfirmDialog
        open={action !== null}
        title={dialogConfig ? t(dialogConfig.titleKey) : ""}
        message={
          action
            ? t(dialogConfig.messageKey, { name: action.store.name })
            : ""
        }
        confirmLabel={dialogConfig ? t(dialogConfig.confirmKey) : ""}
        variant={dialogConfig?.variant}
        loading={working}
        onConfirm={runAction}
        onCancel={() => (working ? null : setAction(null))}
      >
        {action && action.type !== "remove" && (
          <div>
            <label className="mb-1 block text-micro font-medium text-ink-secondary">
              {t("adminStores.noteLabel")}
            </label>
            <textarea
              value={note}
              onChange={(event) => setNote(event.target.value)}
              rows="2"
              className="w-full resize-none rounded-control border border-line-strong px-3 py-2 text-small outline-none focus:border-cedar-ring focus:ring-1 focus:ring-cedar-ring"
            />
          </div>
        )}
      </ConfirmDialog>
    </div>
  );
}

export default AdminStores;
