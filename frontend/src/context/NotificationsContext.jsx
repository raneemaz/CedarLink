import {
  createContext,
  useCallback,
  useContext,
  useEffect,
  useMemo,
  useRef,
  useState,
} from "react";

import api from "../services/api";
import { useAuth } from "./AuthContext";

const NotificationsContext = createContext(null);

const POLL_INTERVAL_MS = 45 * 1000;
const PAGE_SIZE = 20;
// Backend caps `limit` at 50.
const MAX_FETCH = 50;

export function NotificationsProvider({ children }) {
  const { user } = useAuth();
  const userId = user?.id ?? null;

  const [notifications, setNotifications] = useState([]);
  const [unreadCount, setUnreadCount] = useState(0);
  const [total, setTotal] = useState(0);
  const [loading, setLoading] = useState(false);

  // Latest values mirrored into refs so the stable callbacks below can read
  // them without being recreated: activeUserRef gates state writes to the
  // currently-authenticated user; listLengthRef feeds the poll's page size.
  // Synced in an effect rather than during render — writing a ref in render
  // is unsafe under concurrent rendering (react-hooks/refs).
  const activeUserRef = useRef(userId);
  const listLengthRef = useRef(0);

  useEffect(() => {
    activeUserRef.current = userId;
    listLengthRef.current = notifications.length;
  });

  // Reload the first page. Fetches at least as many rows as are currently
  // shown so a poll never shrinks a list the user has paged through.
  const refresh = useCallback(async () => {
    if (activeUserRef.current == null) return;

    const want = Math.min(
      Math.max(PAGE_SIZE, listLengthRef.current),
      MAX_FETCH,
    );

    setLoading(true);
    try {
      const { data } = await api.get("/notifications", {
        params: { limit: want, offset: 0 },
      });

      if (activeUserRef.current == null) return;

      setNotifications(data?.notifications ?? []);
      if (typeof data?.total === "number") setTotal(data.total);
      if (typeof data?.unread_count === "number") {
        setUnreadCount(data.unread_count);
      }
    } catch {
      /* keep last known state */
    } finally {
      setLoading(false);
    }
  }, []);

  const loadMore = useCallback(async () => {
    if (activeUserRef.current == null) return;

    try {
      const { data } = await api.get("/notifications", {
        params: { limit: PAGE_SIZE, offset: listLengthRef.current },
      });

      if (activeUserRef.current == null) return;

      setNotifications((prev) => [...prev, ...(data?.notifications ?? [])]);
      if (typeof data?.total === "number") setTotal(data.total);
      if (typeof data?.unread_count === "number") {
        setUnreadCount(data.unread_count);
      }
    } catch {
      /* keep last known state */
    }
  }, []);

  // Load + poll the list while authenticated; reset on logout.
  useEffect(() => {
    if (userId == null) {
      setNotifications([]);
      setUnreadCount(0);
      setTotal(0);
      setLoading(false);
      return;
    }

    refresh();

    const interval = setInterval(refresh, POLL_INTERVAL_MS);

    const onVisibility = () => {
      if (document.visibilityState === "visible") refresh();
    };
    document.addEventListener("visibilitychange", onVisibility);

    const onExternalUpdate = () => refresh();
    window.addEventListener("notificationsUpdated", onExternalUpdate);

    return () => {
      clearInterval(interval);
      document.removeEventListener("visibilitychange", onVisibility);
      window.removeEventListener("notificationsUpdated", onExternalUpdate);
    };
  }, [userId, refresh]);

  const markRead = useCallback(
    async (id) => {
      setNotifications((prev) =>
        prev.map((n) =>
          n.id === id && !n.is_read ? { ...n, is_read: true } : n,
        ),
      );
      setUnreadCount((prev) => Math.max(0, prev - 1));

      try {
        const { data } = await api.patch(`/notifications/${id}/read`);
        if (typeof data?.unread_count === "number") {
          setUnreadCount(data.unread_count);
        }
      } catch {
        refresh();
      }
    },
    [refresh],
  );

  const markAllRead = useCallback(async () => {
    setNotifications((prev) => prev.map((n) => ({ ...n, is_read: true })));
    setUnreadCount(0);

    try {
      await api.patch("/notifications/read-all");
    } catch {
      refresh();
    }
  }, [refresh]);

  const deleteAll = useCallback(async () => {
    const { data } = await api.delete("/notifications");

    // Wipe local state so the badge, dropdown and page all clear immediately.
    setNotifications([]);
    setUnreadCount(0);
    setTotal(0);

    return data;
  }, []);

  const value = useMemo(
    () => ({
      notifications,
      unreadCount,
      total,
      loading,
      hasMore: notifications.length < total,
      refresh,
      loadMore,
      markRead,
      markAllRead,
      deleteAll,
    }),
    [
      notifications,
      unreadCount,
      total,
      loading,
      refresh,
      loadMore,
      markRead,
      markAllRead,
      deleteAll,
    ],
  );

  return (
    <NotificationsContext.Provider value={value}>
      {children}
    </NotificationsContext.Provider>
  );
}

export function useNotifications() {
  const context = useContext(NotificationsContext);

  if (!context) {
    throw new Error(
      "useNotifications must be used within a NotificationsProvider",
    );
  }

  return context;
}
