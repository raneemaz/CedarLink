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
        className="relative cursor-pointer text-ink-body transition hover:text-cedar"
      >
        <Bell size={24} />

        {badge && (
          <span className="absolute -end-2 -top-2 flex h-5 min-w-[1.25rem] items-center justify-center rounded-full bg-cedar px-1 text-xs text-on-cedar">
            {badge}
          </span>
        )}
      </button>

      {open && (
        <div className="absolute end-0 top-full z-50 mt-2 w-80 overflow-hidden rounded-xl border border-line bg-paper-raised shadow-lg">
          <div className="flex items-center justify-between border-b border-line-subtle px-4 py-3">
            <span className="text-sm font-semibold text-ink">
              {t("notificationsFeed.title")}
            </span>

            <button
              type="button"
              onClick={markAllRead}
              disabled={unreadCount === 0}
              className="text-xs font-medium text-cedar transition hover:underline disabled:cursor-not-allowed disabled:text-ink-disabled"
            >
              {t("notificationsFeed.markAllRead")}
            </button>
          </div>

          <div className="max-h-96 overflow-y-auto">
            {notifications.length === 0 ? (
              <p className="px-4 py-6 text-center text-sm text-ink-muted">
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
                    className={`flex w-full items-start gap-3 border-b border-line-subtle px-4 py-3 text-start transition hover:bg-paper ${
                      notification.is_read ? "" : "bg-cedar-subtle/50"
                    }`}
                  >
                    <span className="mt-0.5 shrink-0 text-cedar">
                      <Icon size={18} />
                    </span>

                    <span className="min-w-0 flex-1">
                      <span className="block truncate text-sm font-medium text-ink">
                        {notification.title}
                      </span>
                      <span className="mt-0.5 block truncate text-xs text-ink-muted">
                        {notification.message}
                      </span>
                      <span className="mt-1 block text-[11px] text-ink-faint">
                        {formatRelativeTime(
                          notification.created_at,
                          i18n.language,
                        )}
                      </span>
                    </span>

                    {!notification.is_read && (
                      <span className="mt-1 h-2 w-2 shrink-0 rounded-full bg-cedar-ring" />
                    )}
                  </button>
                );
              })
            )}
          </div>

          <Link
            to="/notifications"
            onClick={() => setOpen(false)}
            className="block border-t border-line-subtle px-4 py-3 text-center text-sm font-medium text-cedar transition hover:bg-paper"
          >
            {t("notificationsFeed.seeAll")}
          </Link>
        </div>
      )}
    </div>
  );
}

export default NotificationBell;
