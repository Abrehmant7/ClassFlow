import { useCallback, useEffect, useRef, useState } from "react";

import {
  getUnreadCount, listNotifications, markAllNotificationsRead,
  markNotificationRead, markNotificationUnread,
} from "../api/notifications.js";
import { parseModule7Error } from "../utils/module7.js";
import NotificationContext from "./notificationContext.js";

export function NotificationProvider({ children }) {
  const [unreadCount, setUnreadCount] = useState(0);
  const [recent, setRecent] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const mounted = useRef(false);
  const requestVersion = useRef(0);
  const inFlight = useRef(null);
  const mutationCount = useRef(0);

  const refresh = useCallback(() => {
    if (mutationCount.current > 0) return Promise.resolve();
    if (inFlight.current) return inFlight.current;
    const version = ++requestVersion.current;
    const request = Promise.all([
      getUnreadCount(), listNotifications({ page: 1, page_size: 5 }),
    ]).then(([count, list]) => {
      if (!mounted.current || version !== requestVersion.current) return;
      setUnreadCount(Math.max(0, count.unread_count));
      setRecent(list.items);
      setError(null);
    }).catch((apiError) => {
      if (mounted.current && version === requestVersion.current) {
        setError(parseModule7Error(apiError));
      }
    }).finally(() => {
      if (mounted.current && version === requestVersion.current) setLoading(false);
      inFlight.current = null;
    });
    inFlight.current = request;
    return request;
  }, []);

  useEffect(() => {
    mounted.current = true;
    refresh();
    const timer = window.setInterval(refresh, 60_000);
    window.addEventListener("focus", refresh);
    return () => {
      mounted.current = false;
      requestVersion.current += 1;
      window.clearInterval(timer);
      window.removeEventListener("focus", refresh);
    };
  }, [refresh]);

  function resumeInitialLoad() {
    if (!mounted.current || !loading) return;
    const pending = inFlight.current;
    if (pending) pending.then(() => { if (mounted.current) refresh(); });
    else refresh();
  }

  async function changeRead(notification, shouldRead) {
    mutationCount.current += 1;
    requestVersion.current += 1;
    try {
      const updated = shouldRead
        ? await markNotificationRead(notification.id)
        : await markNotificationUnread(notification.id);
      if (mounted.current) {
        setRecent((current) => current.map((item) => item.id === updated.id ? updated : item));
        if (notification.is_read !== updated.is_read) {
          setUnreadCount((current) => Math.max(0, current + (updated.is_read ? -1 : 1)));
        }
      }
      return updated;
    } finally {
      mutationCount.current -= 1;
      resumeInitialLoad();
    }
  }

  async function markAllRead() {
    mutationCount.current += 1;
    requestVersion.current += 1;
    try {
      const result = await markAllNotificationsRead();
      if (mounted.current) {
        setUnreadCount(0);
        setRecent((current) => current.map((item) => ({ ...item, is_read: true })));
      }
      return result;
    } finally {
      mutationCount.current -= 1;
      resumeInitialLoad();
    }
  }

  const value = {
    unreadCount, recent, loading, error, refresh,
    markRead: (item) => changeRead(item, true),
    markUnread: (item) => changeRead(item, false),
    markAllRead,
  };

  return <NotificationContext.Provider value={value}>{children}</NotificationContext.Provider>;
}
