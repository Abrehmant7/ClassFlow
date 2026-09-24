import { Link } from "react-router-dom";

import { formatLocalDate } from "../utils/module7.js";
import Button from "./Button.jsx";

function NotificationItem({ notification, onOpen, onToggleRead, busy = false }) {
  return (
    <article className={`min-w-0 rounded-lg border p-3 ${notification.is_read ? "border-slate-200 bg-white" : "border-blue-200 bg-blue-50"}`}>
      <Link
        className="block min-w-0 rounded cf-focus"
        onClick={(event) => {
          event.preventDefault();
          if (!busy) onOpen(notification);
        }}
        to={notification.action_url}
      >
        <span className="flex items-center gap-2 break-words text-sm font-semibold text-slate-900">
          {!notification.is_read ? <span aria-label="Unread" className="h-2 w-2 shrink-0 rounded-full bg-blue-600" /> : null}
          {notification.title}
        </span>
        <span className="mt-1 block whitespace-pre-wrap break-words text-sm text-slate-600">{notification.message}</span>
        <time className="mt-2 block text-xs text-slate-500" dateTime={notification.created_at}>{formatLocalDate(notification.created_at)}</time>
      </Link>
      {onToggleRead ? (
        <Button className="mt-2 px-2 py-1 text-xs" disabled={busy} onClick={() => onToggleRead(notification)} variant="subtle">
          {notification.is_read ? "Mark unread" : "Mark read"}
        </Button>
      ) : null}
    </article>
  );
}

export default NotificationItem;
