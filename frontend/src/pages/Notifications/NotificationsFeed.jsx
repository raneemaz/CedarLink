import { useEffect, useState } from "react";
import { useNavigate } from "react-router-dom";
import { useTranslation } from "react-i18next";
import { toast } from "react-toastify";
import {
  Bell,
  Package,
  Truck,
  CreditCard,
  XCircle,
  CheckCircle2,
  Trash2,
} from "lucide-react";

import { useAuth } from "../../context/AuthContext";
import { useNotifications } from "../../context/NotificationsContext";
import { formatRelativeTime } from "../../utils/helpers";

const TYPE_ICON = {
  order_placed: Package,
  order_status_changed: CheckCircle2,
  order_canceled: XCircle,
  payment_completed: CreditCard,
  payment_refunded: CreditCard,
  delivery_update: Truck,
};

function NotificationsPage() {
  const navigate = useNavigate();
  const { t, i18n } = useTranslation();
  const { isAuthenticated } = useAuth();
  const {
    notifications,
    unreadCount,
    loading,
    hasMore,
    refresh,
    loadMore,
    markRead,
    markAllRead,
    deleteAll,
  } = useNotifications();

  const [loadingMore, setLoadingMore] = useState(false);
  const [confirmingDelete, setConfirmingDelete] = useState(false);
  const [deleting, setDeleting] = useState(false);

  // Pull the freshest data when the page is opened (the shared context also
  // keeps it current via polling).
  useEffect(() => {
    if (isAuthenticated) refresh();
  }, [isAuthenticated, refresh]);

  const handleLoadMore = async () => {
    setLoadingMore(true);
    try {
      await loadMore();
    } finally {
      setLoadingMore(false);
    }
  };

  const handleRowClick = (notification) => {
    if (!notification.is_read) {
      markRead(notification.id);
    }
    if (notification.link) {
      navigate(notification.link);
    }
  };

  const handleDeleteAll = async () => {
    setDeleting(true);
    try {
      await deleteAll();
      setConfirmingDelete(false);
      toast.success(t("notificationsFeed.deletedAll"));
    } catch (err) {
      console.error("Failed to delete notifications:", err);
      toast.error(t("notificationsFeed.deleteError"));
    } finally {
      setDeleting(false);
    }
  };

  if (!isAuthenticated) {
    return (
      <div className="mx-auto max-w-3xl px-6 py-10">
        <div className="rounded-xl border border-red-200 bg-red-50 p-5">
          <p className="text-red-700">
            {t("notificationsFeed.loadError")}
          </p>
        </div>
      </div>
    );
  }

  if (loading && notifications.length === 0) {
    return (
      <div className="mx-auto max-w-3xl px-6 py-10">
        <p className="text-slate-600">{t("notificationsFeed.loading")}</p>
      </div>
    );
  }

  return (
    <div className="mx-auto max-w-3xl px-6 py-10">
      <div className="mb-6 flex flex-wrap items-end justify-between gap-4">
        <div>
          <h1 className="text-3xl font-bold text-slate-900">
            {t("notificationsFeed.title")}
          </h1>
          <p className="mt-2 text-slate-600">
            {t("notificationsFeed.subtitle")}
          </p>
        </div>

        <div className="flex shrink-0 items-center gap-3">
          <button
            type="button"
            onClick={markAllRead}
            disabled={unreadCount === 0}
            className="cursor-pointer rounded-lg border border-emerald-700 px-4 py-2 text-sm font-medium text-emerald-700 transition hover:bg-emerald-50 disabled:cursor-not-allowed disabled:border-slate-200 disabled:text-slate-300"
          >
            {t("notificationsFeed.markAllRead")}
          </button>

          <button
            type="button"
            onClick={() => setConfirmingDelete(true)}
            disabled={notifications.length === 0}
            className="flex cursor-pointer items-center gap-1.5 rounded-lg border border-red-300 px-4 py-2 text-sm font-medium text-red-600 transition hover:bg-red-50 disabled:cursor-not-allowed disabled:border-slate-200 disabled:text-slate-300"
          >
            <Trash2 size={15} />
            {t("notificationsFeed.deleteAll")}
          </button>
        </div>
      </div>

      {confirmingDelete && notifications.length > 0 && (
        <div className="mb-6 flex flex-wrap items-center justify-between gap-3 rounded-xl border border-red-200 bg-red-50 px-4 py-3">
          <p className="text-sm text-red-700">
            {t("notificationsFeed.deleteAllConfirm")}
          </p>

          <div className="flex items-center gap-2">
            <button
              type="button"
              onClick={() => setConfirmingDelete(false)}
              disabled={deleting}
              className="cursor-pointer rounded-lg border border-slate-300 bg-white px-3 py-1.5 text-sm font-medium text-slate-700 transition hover:bg-slate-50 disabled:opacity-60"
            >
              {t("common.cancel")}
            </button>

            <button
              type="button"
              onClick={handleDeleteAll}
              disabled={deleting}
              className="cursor-pointer rounded-lg bg-red-600 px-3 py-1.5 text-sm font-medium text-white transition hover:bg-red-700 disabled:opacity-60"
            >
              {deleting
                ? t("notificationsFeed.deleting")
                : t("notificationsFeed.deleteAllConfirmButton")}
            </button>
          </div>
        </div>
      )}

      {notifications.length === 0 ? (
        <div className="rounded-2xl border border-slate-200 bg-white py-16 text-center">
          <Bell size={28} className="mx-auto text-slate-300" />
          <p className="mt-3 text-slate-600">
            {t("notificationsFeed.empty")}
          </p>
        </div>
      ) : (
        <ul className="space-y-3">
          {notifications.map((notification) => {
            const Icon = TYPE_ICON[notification.type] || Bell;

            return (
              <li key={notification.id}>
                <button
                  type="button"
                  onClick={() => handleRowClick(notification)}
                  className={`flex w-full cursor-pointer items-start gap-4 rounded-2xl border p-4 text-left shadow-sm transition hover:bg-slate-50 ${
                    notification.is_read
                      ? "border-slate-200 bg-white"
                      : "border-emerald-200 bg-emerald-50/50"
                  }`}
                >
                  <span className="mt-0.5 shrink-0 text-emerald-700">
                    <Icon size={20} />
                  </span>

                  <span className="min-w-0 flex-1">
                    <span className="block font-medium text-slate-900">
                      {notification.title}
                    </span>
                    <span className="mt-1 block text-sm text-slate-600">
                      {notification.message}
                    </span>
                    <span className="mt-2 block text-xs text-slate-400">
                      {formatRelativeTime(
                        notification.created_at,
                        i18n.language,
                      )}
                    </span>
                  </span>

                  {!notification.is_read && (
                    <span className="mt-1 h-2.5 w-2.5 shrink-0 rounded-full bg-emerald-600" />
                  )}
                </button>
              </li>
            );
          })}
        </ul>
      )}

      {hasMore && (
        <div className="mt-6 flex justify-center">
          <button
            type="button"
            onClick={handleLoadMore}
            disabled={loadingMore}
            className="cursor-pointer rounded-lg bg-emerald-700 px-6 py-2.5 text-sm font-medium text-white transition hover:bg-emerald-800 disabled:opacity-60"
          >
            {loadingMore
              ? t("notificationsFeed.loading")
              : t("notificationsFeed.loadMore")}
          </button>
        </div>
      )}
    </div>
  );
}

export default NotificationsPage;
