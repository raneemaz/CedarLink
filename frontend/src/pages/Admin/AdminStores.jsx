import { useEffect, useState } from "react";
import { toast } from "react-toastify";

import api from "../../services/api";
import ConfirmDialog from "../../components/common/ConfirmDialog/ConfirmDialog";

const STATUS_BADGE = {
  active: "bg-emerald-100 text-emerald-700",
  inactive: "bg-amber-100 text-amber-700",
  removed: "bg-gray-200 text-gray-600",
};

function AdminStores() {
  const [stores, setStores] = useState([]);
  const [loading, setLoading] = useState(true);

  const [target, setTarget] = useState(null);
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

  const removeStore = async () => {
    if (!target) return;
    setWorking(true);
    try {
      await api.delete(`/admin/stores/${target.id}`);
      toast.success(`"${target.name}" removed.`);
      await load();
      setTarget(null);
    } catch (error) {
      console.error("Failed to remove store:", error);
      toast.error(
        error.response?.data?.error || "The store could not be removed.",
      );
    } finally {
      setWorking(false);
    }
  };

  if (loading) {
    return <p className="text-sm text-gray-500">Loading stores...</p>;
  }

  return (
    <div>
      <h1 className="mb-6 text-3xl font-bold text-gray-900">Stores</h1>

      <div className="overflow-x-auto rounded-2xl bg-white shadow-sm">
        <table className="min-w-full text-sm">
          <thead>
            <tr className="border-b border-gray-100 text-left text-xs uppercase tracking-wide text-gray-400">
              <th className="px-4 py-3 font-medium">Store</th>
              <th className="px-4 py-3 font-medium">Owner</th>
              <th className="px-4 py-3 font-medium">Products</th>
              <th className="px-4 py-3 font-medium">Status</th>
              <th className="px-4 py-3 font-medium text-right">Actions</th>
            </tr>
          </thead>
          <tbody className="divide-y divide-gray-100">
            {stores.map((store) => (
              <tr key={store.id}>
                <td className="px-4 py-3">
                  <p className="font-medium text-gray-900">{store.name}</p>
                  <p className="text-gray-500">
                    {store.location || "—"}
                  </p>
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
                <td className="px-4 py-3 text-right">
                  {store.status === "removed" ? (
                    <span className="text-xs text-gray-400">—</span>
                  ) : (
                    <button
                      type="button"
                      onClick={() => setTarget(store)}
                      className="font-medium text-red-600 hover:underline"
                    >
                      Remove
                    </button>
                  )}
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>

      <ConfirmDialog
        open={target !== null}
        title="Remove store"
        message={
          target
            ? `Remove "${target.name}"? It disappears from the storefront and its vendor loses access. Orders already placed with this store are kept, and customers keep their order history.`
            : ""
        }
        confirmLabel="Remove store"
        loading={working}
        onConfirm={removeStore}
        onCancel={() => (working ? null : setTarget(null))}
      />
    </div>
  );
}

export default AdminStores;
