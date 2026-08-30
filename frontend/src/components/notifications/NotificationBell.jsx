import { useEffect, useRef, useState } from "react";
import { Link, useNavigate } from "react-router-dom";
import { useTranslation } from "react-i18next";
import {
  Bell,
  Package,
  Truck,
  CreditCard,
  XCircle,
  CheckCircle2,
} from "lucide-react";

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

function NotificationBell() {
  const { t, i18n } = useTranslation();
  const navigate = useNavigate();
  const { unreadCount, notifications, refresh, markRead, markAllRead } =
    useNotifications();

  const [open, setOpen] = useState(false);
  const containerRef = useRef(null);

  // Always show current data the moment the dropdown is opened, without
  // waiting for the next poll.
  useEffect(() => {
    if (open) refresh();
  }, [open, refresh]);

  useEffect(() => {
    if (!open) return;

    const onPointerDown = (event) => {
      if (
        containerRef.current &&
        !containerRef.current.contains(event.target)
      ) {
        setOpen(false);
      }
    };

    document.addEventListener("mousedown", onPointerDown);
    return () => document.removeEventListener("mousedown", onPointerDown);
  }, [open]);

  const badge =
    unreadCount > 9 ? "9+" : unreadCount > 0 ? String(unreadCount) : null;

  const handleRowClick = (notification) => {
    if (!notification.is_read) {
      markRead(notification.id);
    }
    setOpen(false);
    if (notification.link) {
      navigate(notification.link);
    }
  };

  return (
    <div ref={containerRef} className="relative">
      <button
        type="button"
        aria-label={t("navbar.notifications")}
        aria-haspopup="true"
        aria-expanded={open}
        onClick={() => setOpen((value) => !value)}
        className="relative cursor-pointer text-slate-700 transition hover:text-emerald-700"
      >
        <Bell size={24} />

        {badge && (
          <span className="absolute -end-2 -top-2 flex h-5 min-w-[1.25rem] items-center justify-center rounded-full bg-emerald-700 px-1 text-xs text-white">
            {badge}
          </span>
        )}
      </button>

      {open && (
        <div className="absolute end-0 top-full z-50 mt-2 w-80 overflow-hidden rounded-xl border border-slate-200 bg-white shadow-lg">
          <div className="flex items-center justify-between border-b border-slate-100 px-4 py-3">
            <span className="text-sm font-semibold text-slate-900">
              {t("notificationsFeed.title")}
            </span>

            <button
              type="button"
              onClick={markAllRead}
              disabled={unreadCount === 0}
              className="text-xs font-medium text-emerald-700 transition hover:underline disabled:cursor-not-allowed disabled:text-slate-300"
            >
              {t("notificationsFeed.markAllRead")}
            </button>
          </div>

          <div className="max-h-96 overflow-y-auto">
            {notifications.length === 0 ? (
              <p className="px-4 py-6 text-center text-sm text-slate-500">
                {t("notificationsFeed.empty")}
              </p>
            ) : (
              notifications.slice(0, 5).map((notification) => {
                const Icon = TYPE_ICON[notification.type] || Bell;

                return (
                  <button
                    type="button"
                    key={notification.id}
                    onClick={() => handleRowClick(notification)}
                    className={`flex w-full items-start gap-3 border-b border-slate-50 px-4 py-3 text-start transition hover:bg-slate-50 ${
                      notification.is_read ? "" : "bg-emerald-50/50"
                    }`}
                  >
                    <span className="mt-0.5 shrink-0 text-emerald-700">
                      <Icon size={18} />
                    </span>

                    <span className="min-w-0 flex-1">
                      <span className="block truncate text-sm font-medium text-slate-900">
                        {notification.title}
                      </span>
                      <span className="mt-0.5 block truncate text-xs text-slate-500">
                        {notification.message}
                      </span>
                      <span className="mt-1 block text-[11px] text-slate-400">
                        {formatRelativeTime(
                          notification.created_at,
                          i18n.language,
                        )}
                      </span>
                    </span>

                    {!notification.is_read && (
                      <span className="mt-1 h-2 w-2 shrink-0 rounded-full bg-emerald-600" />
                    )}
                  </button>
                );
              })
            )}
          </div>

          <Link
            to="/notifications"
            onClick={() => setOpen(false)}
            className="block border-t border-slate-100 px-4 py-3 text-center text-sm font-medium text-emerald-700 transition hover:bg-slate-50"
          >
            {t("notificationsFeed.seeAll")}
          </Link>
        </div>
      )}
    </div>
  );
}

export default NotificationBell;
