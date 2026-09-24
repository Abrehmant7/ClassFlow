import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import { useNavigate, useSearchParams } from "react-router-dom";

import { listNotifications } from "../api/notifications.js";
import Alert from "../components/Alert.jsx";
import Button from "../components/Button.jsx";
import EmptyState from "../components/EmptyState.jsx";
import NotificationItem from "../components/NotificationItem.jsx";
import Pagination from "../components/Pagination.jsx";
import useNotifications from "../notifications/useNotifications.js";
import { NOTIFICATION_EVENTS, parseModule7Error } from "../utils/module7.js";

const PAGE_SIZE = 20;

function NotificationsPage() {
  const [searchParams, setSearchParams] = useSearchParams();
  const unreadOnly = searchParams.get("unread_only") === "true";
  const eventType = searchParams.get("event_type") || "";
  const page = Math.max(1, Number(searchParams.get("page")) || 1);
  const navigate = useNavigate();
  const { markRead, markUnread, markAllRead } = useNotifications();
  const [data, setData] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [actionError, setActionError] = useState(null);
  const [busyId, setBusyId] = useState(null);
  const requestVersion = useRef(0);
  const actionInFlight = useRef(false);
  const params = useMemo(() => ({
    page, page_size: PAGE_SIZE,
    ...(unreadOnly ? { unread_only: true } : {}),
    ...(eventType ? { event_type: eventType } : {}),
  }), [page, unreadOnly, eventType]);

  const load = useCallback(async () => {
    const version = ++requestVersion.current;
    setData(null);
    setLoading(true);
    setError(null);
    try {
      const result = await listNotifications(params);
      if (version === requestVersion.current) setData(result);
    } catch (apiError) {
      if (version === requestVersion.current) {
        setData(null);
        setError(parseModule7Error(apiError));
      }
    } finally {
      if (version === requestVersion.current) setLoading(false);
    }
  }, [params]);

  useEffect(() => {
    load();
    return () => { requestVersion.current += 1; };
  }, [load]);

  function updateFilter(updates) {
    const next = new URLSearchParams(searchParams);
    for (const [key, value] of Object.entries(updates)) {
      if (value) next.set(key, String(value));
      else next.delete(key);
    }
    if (!("page" in updates)) next.delete("page");
    setSearchParams(next);
  }

  async function perform(operation) {
    if (actionInFlight.current) return;
    actionInFlight.current = true;
    setBusyId(operation.id);
    setActionError(null);
    try {
      const updated = await operation.run();
      if (operation.id !== "all") {
        setData((current) => current ? ({
          ...current,
          items: current.items.map((item) => item.id === updated.id ? updated : item),
        }) : current);
      } else {
        setData((current) => current ? ({
          ...current,
          items: current.items.map((item) => ({ ...item, is_read: true })),
        }) : current);
      }
      if (operation.openUrl) navigate(operation.openUrl);
      else await load();
    } catch (apiError) {
      setActionError(parseModule7Error(apiError));
    } finally {
      actionInFlight.current = false;
      setBusyId(null);
    }
  }

  return (
    <section className="space-y-6">
      <div className="flex flex-wrap items-end justify-between gap-3">
        <div>
          <p className="text-xs font-semibold uppercase tracking-wide text-cyan-700">Inbox</p>
          <h1 className="mt-1 text-2xl font-bold text-slate-900">Notifications</h1>
        </div>
        <Button disabled={busyId !== null} onClick={() => perform({ id: "all", run: markAllRead })}>Mark all as read</Button>
      </div>

      <div className="cf-card grid gap-4 p-4 sm:grid-cols-2">
        <div>
          <label className="cf-label" htmlFor="notification-view">Show</label>
          <select className="cf-input" id="notification-view" onChange={(event) => updateFilter({ unread_only: event.target.value })} value={unreadOnly ? "true" : ""}>
            <option value="">All notifications</option>
            <option value="true">Unread only</option>
          </select>
        </div>
        <div>
          <label className="cf-label" htmlFor="notification-event">Event type</label>
          <select className="cf-input" id="notification-event" onChange={(event) => updateFilter({ event_type: event.target.value })} value={eventType}>
            <option value="">All events</option>
            {NOTIFICATION_EVENTS.map(([value, label]) => <option key={value} value={value}>{label}</option>)}
          </select>
        </div>
      </div>

      {actionError ? <Alert title="Notification action failed" {...actionError} /> : null}
      {error ? <div className="space-y-3"><Alert title="Could not load notifications" {...error} /><Button onClick={load}>Try again</Button></div> : null}
      {loading ? <p className="text-sm text-slate-500" role="status">Loading notifications...</p> : null}
      {!loading && !error && data?.items.length === 0 ? <EmptyState title="No notifications found" message={unreadOnly ? "You have no unread notifications matching these filters." : "Notifications will appear here when class activity occurs."} /> : null}
      {!error && data?.items.length > 0 ? (
        <div className="space-y-3" aria-label="Notification list">
          {data.items.map((item) => (
            <NotificationItem busy={busyId !== null} key={item.id} notification={item}
              onOpen={(notification) => {
                if (notification.is_read) navigate(notification.action_url);
                else perform({ id: notification.id, run: () => markRead(notification), openUrl: notification.action_url });
              }}
              onToggleRead={(notification) => perform({
                id: notification.id,
                run: () => notification.is_read ? markUnread(notification) : markRead(notification),
              })} />
          ))}
        </div>
      ) : null}
      {!error && data ? (
        <Pagination disabled={loading || busyId !== null} page={data.page}
          totalPages={Math.ceil(data.total / data.page_size)} onChange={(next) => updateFilter({ page: next })} />
      ) : null}
    </section>
  );
}

export default NotificationsPage;
