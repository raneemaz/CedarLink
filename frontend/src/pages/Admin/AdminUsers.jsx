import { useEffect, useMemo, useState } from "react";
import { useTranslation } from "react-i18next";
import { toast } from "react-toastify";

import api from "../../services/api";
import ConfirmDialog from "../../components/common/ConfirmDialog/ConfirmDialog";

const STATUS_BADGE = {
  active: "bg-success-subtle text-success",
  suspended: "bg-danger-tint text-danger-strong",
  deactivated: "bg-warning-tint text-warning-muted",
  deleted: "bg-control text-ink-secondary",
};

function currentUserId() {
  try {
    return JSON.parse(localStorage.getItem("user"))?.id ?? null;
  } catch {
    return null;
  }
}

function AdminUsers() {
  const { t } = useTranslation();
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
          toast.error(t("adminUsers.errLoad"));
        }
      } finally {
        if (!cancelled) setLoading(false);
      }
    })();
    return () => {
      cancelled = true;
    };
  }, [t]);

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
        toast.success(t("adminUsers.toastSuspended", { email: target.user.email }));
      } else {
        await api.patch(`/admin/users/${target.user.id}/unsuspend`);
        toast.success(t("adminUsers.toastUnsuspended", { email: target.user.email }));
      }
      await load();
      setTarget(null);
    } catch (error) {
      console.error("User action failed:", error);
      toast.error(
        error.response?.data?.error || t("adminUsers.errAction"),
      );
    } finally {
      setWorking(false);
    }
  };

  if (loading) {
    return <p className="text-sm text-ink-muted">{t("adminUsers.loading")}</p>;
  }

  return (
    <div>
      <div className="mb-6 flex flex-wrap items-center justify-between gap-3">
        <h1 className="text-3xl font-bold text-ink">{t("adminUsers.title")}</h1>
        <input
          type="text"
          value={search}
          onChange={(event) => setSearch(event.target.value)}
          placeholder={t("adminUsers.searchPlaceholder")}
          className="rounded-md border border-line-strong px-3 py-2 text-sm outline-none focus:border-cedar-ring"
        />
      </div>

      <div className="overflow-x-auto rounded-2xl bg-paper-raised shadow-sm">
        <table className="min-w-full text-sm">
          <thead>
            <tr className="border-b border-line-subtle text-start text-xs uppercase tracking-wide text-ink-faint">
              <th className="px-4 py-3 font-medium">{t("adminUsers.colUser")}</th>
              <th className="px-4 py-3 font-medium">{t("adminUsers.colRole")}</th>
              <th className="px-4 py-3 font-medium">{t("adminUsers.colStatus")}</th>
              <th className="px-4 py-3 font-medium text-end">{t("adminUsers.colActions")}</th>
            </tr>
          </thead>
          <tbody className="divide-y divide-line-subtle">
            {filtered.map((user) => {
              const isSelf = user.id === meId;
              const isAdmin = user.role === "admin";

              return (
                <tr key={user.id}>
                  <td className="px-4 py-3">
                    <p className="font-medium text-ink">
                      {user.first_name} {user.last_name}
                    </p>
                    <p className="text-ink-muted">{user.email}</p>
                    {user.status === "suspended" &&
                      user.suspension_reason && (
                        <p className="mt-1 text-xs text-danger">
                          {t("adminUsers.reasonPrefix", { reason: user.suspension_reason })}
                        </p>
                      )}
                  </td>
                  <td className="px-4 py-3 text-ink-secondary">
                    {t(`role.${user.role}`)}
                  </td>
                  <td className="px-4 py-3">
                    <span
                      className={`rounded-full px-2.5 py-1 text-xs font-semibold ${
                        STATUS_BADGE[user.status] || STATUS_BADGE.active
                      }`}
                    >
                      {t(`userStatus.${user.status}`)}
                    </span>
                  </td>
                  <td className="px-4 py-3 text-end">
                    {isAdmin || isSelf ? (
                      <span className="text-xs text-ink-faint">—</span>
                    ) : user.status === "suspended" ? (
                      <button
                        type="button"
                        onClick={() => openUnsuspend(user)}
                        className="font-medium text-cedar hover:underline"
                      >
                        {t("adminUsers.unsuspend")}
                      </button>
                    ) : (
                      <button
                        type="button"
                        onClick={() => openSuspend(user)}
                        className="font-medium text-danger hover:underline"
                      >
                        {t("adminUsers.suspend")}
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
          target?.type === "suspend"
            ? t("adminUsers.dialogSuspendTitle")
            : t("adminUsers.dialogUnsuspendTitle")
        }
        message={
          target
            ? target.type === "suspend"
              ? t("adminUsers.dialogSuspendMessage", { email: target.user.email })
              : t("adminUsers.dialogUnsuspendMessage", { email: target.user.email })
            : ""
        }
        confirmLabel={
          target?.type === "suspend"
            ? t("adminUsers.suspend")
            : t("adminUsers.unsuspend")
        }
        variant={target?.type === "suspend" ? "danger" : "primary"}
        loading={working}
        onConfirm={runAction}
        onCancel={closeDialog}
      >
        {target?.type === "suspend" && (
          <div>
            <label className="mb-1 block text-xs font-medium text-ink-secondary">
              {t("adminUsers.reasonLabel")}
            </label>
            <textarea
              value={reason}
              onChange={(event) => setReason(event.target.value)}
              rows="2"
              className="w-full resize-none rounded-lg border border-line-strong px-3 py-2 text-sm outline-none focus:border-cedar-ring focus:ring-1 focus:ring-cedar-ring"
            />
          </div>
        )}
      </ConfirmDialog>
    </div>
  );
}

export default AdminUsers;
