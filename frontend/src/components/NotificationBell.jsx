import { useEffect, useRef, useState } from "react";
import { Link, useNavigate } from "react-router-dom";

import useNotifications from "../notifications/useNotifications.js";
import { parseModule7Error } from "../utils/module7.js";
import Alert from "./Alert.jsx";
import Button from "./Button.jsx";
import NotificationItem from "./NotificationItem.jsx";

function NotificationBell() {
  const { unreadCount, recent, loading, error, refresh, markRead, markAllRead } = useNotifications();
  const [open, setOpen] = useState(false);
  const [actionError, setActionError] = useState(null);
  const [busy, setBusy] = useState(false);
  const rootRef = useRef(null);
  const buttonRef = useRef(null);
  const navigate = useNavigate();

  useEffect(() => {
    if (!open) return undefined;
    function onPointerDown(event) {
      if (!rootRef.current?.contains(event.target)) setOpen(false);
    }
    function onKeyDown(event) {
      if (event.key === "Escape") {
        setOpen(false);
        buttonRef.current?.focus();
      }
    }
    document.addEventListener("pointerdown", onPointerDown);
    document.addEventListener("keydown", onKeyDown);
    return () => {
      document.removeEventListener("pointerdown", onPointerDown);
      document.removeEventListener("keydown", onKeyDown);
    };
  }, [open]);

  async function openNotification(notification) {
    if (busy) return;
    setBusy(true);
    setActionError(null);
    try {
      if (!notification.is_read) await markRead(notification);
      setOpen(false);
      navigate(notification.action_url);
    } catch (apiError) {
      setActionError(parseModule7Error(apiError));
    } finally {
      setBusy(false);
    }
  }

  async function readAll() {
    if (busy) return;
    setBusy(true);
    setActionError(null);
    try {
      await markAllRead();
    } catch (apiError) {
      setActionError(parseModule7Error(apiError));
    } finally {
      setBusy(false);
    }
  }

  return (
    <div className="relative" ref={rootRef}>
      <button aria-expanded={open} aria-haspopup="true" aria-label={`Notifications, ${unreadCount} unread`}
        className="relative flex min-h-10 min-w-10 items-center justify-center rounded-lg border border-slate-200 text-slate-700 hover:bg-slate-50 cf-focus"
        onClick={() => setOpen((current) => !current)} ref={buttonRef} type="button">
        <svg aria-hidden="true" className="h-5 w-5" fill="none" stroke="currentColor" strokeWidth="1.8" viewBox="0 0 24 24">
          <path strokeLinecap="round" strokeLinejoin="round" d="M18 8a6 6 0 0 0-12 0c0 7-3 7-3 9h18c0-2-3-2-3-9ZM10 21h4" />
        </svg>
        {unreadCount > 0 ? <span aria-label={`${unreadCount} unread notifications`} className="absolute -right-2 -top-2 rounded-full bg-red-600 px-1.5 py-0.5 text-xs font-bold text-white">{unreadCount > 99 ? "99+" : unreadCount}</span> : null}
      </button>
      {open ? (
        <div aria-label="Recent notifications" className="absolute right-0 z-50 mt-2 w-[min(22rem,calc(100vw-2rem))] space-y-3 rounded-lg border border-slate-200 bg-white p-3 shadow-xl" role="region">
          <div className="flex items-center justify-between gap-2">
            <h2 className="text-sm font-semibold text-slate-900">Notifications</h2>
            <Button className="px-2 py-1 text-xs" disabled={busy || unreadCount === 0} onClick={readAll} variant="subtle">Mark all as read</Button>
          </div>
          {loading ? <p className="text-sm text-slate-500" role="status">Loading notifications...</p> : null}
          {error ? <><Alert title="Could not load notifications" {...error} /><Button onClick={refresh}>Try again</Button></> : null}
          {actionError ? <Alert title="Notification action failed" {...actionError} /> : null}
          {!loading && !error && recent.length === 0 ? <p className="text-sm text-slate-500">No notifications yet.</p> : null}
          {!error ? <div className="max-h-96 space-y-2 overflow-y-auto">{recent.slice(0, 5).map((item) => <NotificationItem busy={busy} key={item.id} notification={item} onOpen={openNotification} />)}</div> : null}
          <Link className="block rounded text-center text-sm font-semibold text-blue-700 hover:text-blue-900 cf-focus" onClick={() => setOpen(false)} to="/notifications">View all</Link>
        </div>
      ) : null}
    </div>
  );
}

export default NotificationBell;
