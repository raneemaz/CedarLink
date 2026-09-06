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

function NotificationsFeed() {
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
        <div className="rounded-xl border border-danger-border bg-danger-subtle p-5">
          <p className="text-danger-strong">
            {t("notificationsFeed.loadError")}
          </p>
        </div>
      </div>
    );
  }

  if (loading && notifications.length === 0) {
    return (
      <div className="mx-auto max-w-3xl px-6 py-10">
        <p className="text-ink-secondary">{t("notificationsFeed.loading")}</p>
      </div>
    );
  }

  return (
    <div className="mx-auto max-w-3xl px-6 py-10">
      <div className="mb-6 flex flex-wrap items-end justify-between gap-4">
        <div>
          <h1 className="text-3xl font-bold text-ink">
            {t("notificationsFeed.title")}
          </h1>
          <p className="mt-2 text-ink-secondary">
            {t("notificationsFeed.subtitle")}
          </p>
        </div>

        <div className="flex shrink-0 items-center gap-3">
          <button
            type="button"
            onClick={markAllRead}
            disabled={unreadCount === 0}
            className="cursor-pointer rounded-lg border border-cedar px-4 py-2 text-sm font-medium text-cedar transition hover:bg-cedar-subtle disabled:cursor-not-allowed disabled:border-line disabled:text-ink-disabled"
          >
            {t("notificationsFeed.markAllRead")}
          </button>

          <button
            type="button"
            onClick={() => setConfirmingDelete(true)}
            disabled={notifications.length === 0}
            className="flex cursor-pointer items-center gap-1.5 rounded-lg border border-danger-border px-4 py-2 text-sm font-medium text-danger transition hover:bg-danger-subtle disabled:cursor-not-allowed disabled:border-line disabled:text-ink-disabled"
          >
            <Trash2 size={15} />
            {t("notificationsFeed.deleteAll")}
          </button>
        </div>
      </div>

      {confirmingDelete && notifications.length > 0 && (
        <div className="mb-6 flex flex-wrap items-center justify-between gap-3 rounded-xl border border-danger-border bg-danger-subtle px-4 py-3">
          <p className="text-sm text-danger-strong">
            {t("notificationsFeed.deleteAllConfirm")}
          </p>

          <div className="flex items-center gap-2">
            <button
              type="button"
              onClick={() => setConfirmingDelete(false)}
              disabled={deleting}
              className="cursor-pointer rounded-lg border border-line-strong bg-paper-raised px-3 py-1.5 text-sm font-medium text-ink-body transition hover:bg-paper disabled:opacity-60"
            >
              {t("common.cancel")}
            </button>

            <button
              type="button"
              onClick={handleDeleteAll}
              disabled={deleting}
              className="cursor-pointer rounded-lg bg-danger px-3 py-1.5 text-sm font-medium text-on-danger transition hover:bg-danger-strong disabled:opacity-60"
            >
              {deleting
                ? t("notificationsFeed.deleting")
                : t("notificationsFeed.deleteAllConfirmButton")}
            </button>
          </div>
        </div>
      )}

      {notifications.length === 0 ? (
        <div className="rounded-2xl border border-line bg-paper-raised py-16 text-center">
          <Bell size={28} className="mx-auto text-ink-disabled" />
          <p className="mt-3 text-ink-secondary">
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
                  className={`flex w-full cursor-pointer items-start gap-4 rounded-2xl border p-4 text-start shadow-sm transition hover:bg-paper ${
                    notification.is_read
                      ? "border-line bg-paper-raised"
                      : "border-cedar-tint bg-cedar-subtle/50"
                  }`}
                >
                  <span className="mt-0.5 shrink-0 text-cedar">
                    <Icon size={20} />
                  </span>

                  <span className="min-w-0 flex-1">
                    <span className="block font-medium text-ink">
                      {notification.title}
                    </span>
                    <span className="mt-1 block text-sm text-ink-secondary">
                      {notification.message}
                    </span>
                    <span className="mt-2 block text-xs text-ink-faint">
                      {formatRelativeTime(
                        notification.created_at,
                        i18n.language,
                      )}
                    </span>
                  </span>

                  {!notification.is_read && (
                    <span className="mt-1 h-2.5 w-2.5 shrink-0 rounded-full bg-cedar-ring" />
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
            className="cursor-pointer rounded-lg bg-cedar px-6 py-2.5 text-sm font-medium text-on-cedar transition hover:bg-cedar-strong disabled:opacity-60"
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

export default NotificationsFeed;
