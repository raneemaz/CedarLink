import { useEffect, useMemo, useState } from "react";
import { toast } from "react-toastify";

import api from "../../services/api";
import ConfirmDialog from "../../components/common/ConfirmDialog/ConfirmDialog";

const STATUS_BADGE = {
  active: "bg-emerald-100 text-emerald-700",
  suspended: "bg-red-100 text-red-700",
  deactivated: "bg-amber-100 text-amber-700",
  deleted: "bg-gray-200 text-gray-600",
};

function currentUserId() {
  try {
    return JSON.parse(localStorage.getItem("user"))?.id ?? null;
  } catch {
    return null;
  }
}

function AdminUsers() {
  const [users, setUsers] = useState([]);
  const [loading, setLoading] = useState(true);
  const [search, setSearch] = useState("");

  const [target, setTarget] = useState(null); // { user, type }
  const [reason, setReason] = useState("");
  const [working, setWorking] = useState(false);

  const meId = currentUserId();

  const load = async () => {
    const response = await api.get("/admin/users");
    setUsers(response.data || []);
  };

  useEffect(() => {
    let cancelled = false;
    (async () => {
      try {
        await load();
      } catch (error) {
        if (!cancelled) {
          console.error("Failed to load users:", error);
          toast.error("Unable to load users.");
        }
      } finally {
        if (!cancelled) setLoading(false);
      }
    })();
    return () => {
      cancelled = true;
    };
  }, []);

  const filtered = useMemo(() => {
    const query = search.trim().toLowerCase();
    if (!query) return users;
    return users.filter(
      (user) =>
        `${user.first_name} ${user.last_name}`
          .toLowerCase()
          .includes(query) || user.email.toLowerCase().includes(query),
    );
  }, [users, search]);

  const openSuspend = (user) => {
    setReason("");
    setTarget({ user, type: "suspend" });
  };

  const openUnsuspend = (user) => setTarget({ user, type: "unsuspend" });

  const closeDialog = () => {
    if (!working) setTarget(null);
  };

  const runAction = async () => {
    if (!target) return;
    setWorking(true);
    try {
      if (target.type === "suspend") {
        await api.patch(`/admin/users/${target.user.id}/suspend`, {
          reason: reason.trim(),
        });
        toast.success(`${target.user.email} suspended.`);
      } else {
        await api.patch(`/admin/users/${target.user.id}/unsuspend`);
        toast.success(`${target.user.email} unsuspended.`);
      }
      await load();
      setTarget(null);
    } catch (error) {
      console.error("User action failed:", error);
      toast.error(
        error.response?.data?.error || "The action could not be completed.",
      );
    } finally {
      setWorking(false);
    }
  };

  if (loading) {
    return <p className="text-sm text-gray-500">Loading users...</p>;
  }

  return (
    <div>
      <div className="mb-6 flex flex-wrap items-center justify-between gap-3">
        <h1 className="text-3xl font-bold text-gray-900">Users</h1>
        <input
          type="text"
          value={search}
          onChange={(event) => setSearch(event.target.value)}
          placeholder="Search name or email..."
          className="rounded-md border border-gray-300 px-3 py-2 text-sm outline-none focus:border-emerald-600"
        />
      </div>

      <div className="overflow-x-auto rounded-2xl bg-white shadow-sm">
        <table className="min-w-full text-sm">
          <thead>
            <tr className="border-b border-gray-100 text-left text-xs uppercase tracking-wide text-gray-400">
              <th className="px-4 py-3 font-medium">User</th>
              <th className="px-4 py-3 font-medium">Role</th>
              <th className="px-4 py-3 font-medium">Status</th>
              <th className="px-4 py-3 font-medium text-right">Actions</th>
            </tr>
          </thead>
          <tbody className="divide-y divide-gray-100">
            {filtered.map((user) => {
              const isSelf = user.id === meId;
              const isAdmin = user.role === "admin";

              return (
                <tr key={user.id}>
                  <td className="px-4 py-3">
                    <p className="font-medium text-gray-900">
                      {user.first_name} {user.last_name}
                    </p>
                    <p className="text-gray-500">{user.email}</p>
                    {user.status === "suspended" &&
                      user.suspension_reason && (
                        <p className="mt-1 text-xs text-red-600">
                          Reason: {user.suspension_reason}
                        </p>
                      )}
                  </td>
                  <td className="px-4 py-3 capitalize text-gray-600">
                    {user.role}
                  </td>
                  <td className="px-4 py-3">
                    <span
                      className={`rounded-full px-2.5 py-1 text-xs font-semibold ${
                        STATUS_BADGE[user.status] || STATUS_BADGE.active
                      }`}
                    >
                      {user.status}
                    </span>
                  </td>
                  <td className="px-4 py-3 text-right">
                    {isAdmin || isSelf ? (
                      <span className="text-xs text-gray-400">—</span>
                    ) : user.status === "suspended" ? (
                      <button
                        type="button"
                        onClick={() => openUnsuspend(user)}
                        className="font-medium text-emerald-700 hover:underline"
                      >
                        Unsuspend
                      </button>
                    ) : (
                      <button
                        type="button"
                        onClick={() => openSuspend(user)}
                        className="font-medium text-red-600 hover:underline"
                      >
                        Suspend
                      </button>
                    )}
                  </td>
                </tr>
              );
            })}
          </tbody>
        </table>
      </div>

      <ConfirmDialog
        open={target !== null}
        title={
          target?.type === "suspend" ? "Suspend user" : "Unsuspend user"
        }
        message={
          target
            ? target.type === "suspend"
              ? `Suspend ${target.user.email}? They will not be able to log in or reactivate their account.`
              : `Unsuspend ${target.user.email}? They will be able to log in again.`
            : ""
        }
        confirmLabel={target?.type === "suspend" ? "Suspend" : "Unsuspend"}
        variant={target?.type === "suspend" ? "danger" : "primary"}
        loading={working}
        onConfirm={runAction}
        onCancel={closeDialog}
      >
        {target?.type === "suspend" && (
          <div>
            <label className="mb-1 block text-xs font-medium text-gray-600">
              Reason (optional, shown to the user)
            </label>
            <textarea
              value={reason}
              onChange={(event) => setReason(event.target.value)}
              rows="2"
              className="w-full resize-none rounded-lg border border-gray-300 px-3 py-2 text-sm outline-none focus:border-green-600 focus:ring-1 focus:ring-green-600"
            />
          </div>
        )}
      </ConfirmDialog>
    </div>
  );
}

export default AdminUsers;
