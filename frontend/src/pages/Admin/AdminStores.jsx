import { useEffect, useMemo, useState } from "react";
import { toast } from "react-toastify";

import api from "../../services/api";
import ConfirmDialog from "../../components/common/ConfirmDialog/ConfirmDialog";

const STATUS_BADGE = {
  pending: "bg-blue-100 text-blue-700",
  active: "bg-emerald-100 text-emerald-700",
  inactive: "bg-amber-100 text-amber-700",
  rejected: "bg-red-100 text-red-700",
  removed: "bg-gray-200 text-gray-600",
};

const DIALOG = {
  approve: {
    title: "Approve store",
    confirmLabel: "Approve",
    variant: "primary",
    message: (name) =>
      `Approve "${name}"? It becomes visible on the storefront immediately.`,
  },
  reject: {
    title: "Reject store",
    confirmLabel: "Reject",
    variant: "danger",
    message: (name) =>
      `Reject "${name}"? It stays hidden from the storefront. The vendor keeps their console.`,
  },
  remove: {
    title: "Remove store",
    confirmLabel: "Remove store",
    variant: "danger",
    message: (name) =>
      `Remove "${name}"? It disappears from the storefront and its vendor loses access. Orders already placed with this store are kept, and customers keep their order history.`,
  },
};

function AdminStores() {
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
          toast.error("Unable to load stores.");
        }
      } finally {
        if (!cancelled) setLoading(false);
      }
    })();
    return () => {
      cancelled = true;
    };
  }, []);

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
        toast.success(`"${store.name}" removed.`);
      } else {
        await api.patch(`/admin/stores/${store.id}/${type}`, {
          note: note.trim(),
        });
        toast.success(
          `"${store.name}" ${type === "approve" ? "approved" : "rejected"}.`,
        );
      }
      await load();
      setAction(null);
    } catch (error) {
      console.error("Store action failed:", error);
      toast.error(
        error.response?.data?.error || "The action could not be completed.",
      );
    } finally {
      setWorking(false);
    }
  };

  if (loading) {
    return <p className="text-sm text-gray-500">Loading stores...</p>;
  }

  const dialogConfig = action ? DIALOG[action.type] : null;

  return (
    <div>
      <h1 className="mb-6 text-3xl font-bold text-gray-900">Stores</h1>

      <div className="mb-4 flex gap-2">
        {[
          { key: "all", label: "All" },
          { key: "pending", label: `Pending (${pendingCount})` },
        ].map(({ key, label }) => (
          <button
            key={key}
            type="button"
            onClick={() => setFilter(key)}
            className={`rounded-full px-4 py-1.5 text-sm font-medium transition ${
              filter === key
                ? "bg-emerald-700 text-white"
                : "bg-white text-gray-600 shadow-sm hover:bg-gray-50"
            }`}
          >
            {label}
          </button>
        ))}
      </div>

      <div className="overflow-x-auto rounded-2xl bg-white shadow-sm">
        <table className="min-w-full text-sm">
          <thead>
            <tr className="border-b border-gray-100 text-start text-xs uppercase tracking-wide text-gray-400">
              <th className="px-4 py-3 font-medium">Store</th>
              <th className="px-4 py-3 font-medium">Owner</th>
              <th className="px-4 py-3 font-medium">Products</th>
              <th className="px-4 py-3 font-medium">Status</th>
              <th className="px-4 py-3 font-medium text-end">Actions</th>
            </tr>
          </thead>
          <tbody className="divide-y divide-gray-100">
            {visible.map((store) => (
              <tr key={store.id}>
                <td className="px-4 py-3">
                  <p className="font-medium text-gray-900">{store.name}</p>
                  <p className="text-gray-500">{store.location || "—"}</p>
                  {store.approval_note && (
                    <p className="mt-1 text-xs text-gray-400">
                      Note: {store.approval_note}
                    </p>
                  )}
                </td>
                <td className="px-4 py-3 text-gray-600">
                  <p>{store.owner_name || "—"}</p>
                  <p className="text-gray-400">{store.owner_email}</p>
                </td>
                <td className="px-4 py-3 text-gray-900">
                  {store.product_count}
                </td>
                <td className="px-4 py-3">
                  <span
                    className={`rounded-full px-2.5 py-1 text-xs font-semibold ${
                      STATUS_BADGE[store.status] || STATUS_BADGE.active
                    }`}
                  >
                    {store.status}
                  </span>
                </td>
                <td className="px-4 py-3">
                  <div className="flex justify-end gap-4">
                    {store.status === "removed" ? (
                      <span className="text-xs text-gray-400">—</span>
                    ) : (
                      <>
                        {(store.status === "pending" ||
                          store.status === "rejected") && (
                          <button
                            type="button"
                            onClick={() => open(store, "approve")}
                            className="font-medium text-emerald-700 hover:underline"
                          >
                            Approve
                          </button>
                        )}
                        {store.status === "pending" && (
                          <button
                            type="button"
                            onClick={() => open(store, "reject")}
                            className="font-medium text-amber-700 hover:underline"
                          >
                            Reject
                          </button>
                        )}
                        <button
                          type="button"
                          onClick={() => open(store, "remove")}
                          className="font-medium text-red-600 hover:underline"
                        >
                          Remove
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
        title={dialogConfig?.title}
        message={action ? dialogConfig.message(action.store.name) : ""}
        confirmLabel={dialogConfig?.confirmLabel}
        variant={dialogConfig?.variant}
        loading={working}
        onConfirm={runAction}
        onCancel={() => (working ? null : setAction(null))}
      >
        {action && action.type !== "remove" && (
          <div>
            <label className="mb-1 block text-xs font-medium text-gray-600">
              Note (optional, shown to the vendor)
            </label>
            <textarea
              value={note}
              onChange={(event) => setNote(event.target.value)}
              rows="2"
              className="w-full resize-none rounded-lg border border-gray-300 px-3 py-2 text-sm outline-none focus:border-green-600 focus:ring-1 focus:ring-green-600"
            />
          </div>
        )}
      </ConfirmDialog>
    </div>
  );
}

export default AdminStores;
