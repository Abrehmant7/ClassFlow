import { useCallback, useEffect, useRef, useState } from "react";
import { Link, useNavigate } from "react-router-dom";

import { getDashboard } from "../api/dashboard.js";
import Alert from "../components/Alert.jsx";
import Button from "../components/Button.jsx";
import EmptyState from "../components/EmptyState.jsx";
import NotificationItem from "../components/NotificationItem.jsx";
import StatusBadge from "../components/StatusBadge.jsx";
import TaskRow from "../components/TaskRow.jsx";
import useNotifications from "../notifications/useNotifications.js";
import { browserTimezone, formatLocalDate, parseModule7Error } from "../utils/module7.js";
import PersonalFeedPage from "./PersonalFeedPage.jsx";

function SummaryCard({ label, value }) {
  return (
    <div className="cf-card p-4">
      <h2 className="text-xs font-semibold uppercase tracking-wide text-slate-500">{label}</h2>
      <p className="mt-2 text-3xl font-bold tabular-nums text-slate-900">{value}</p>
    </div>
  );
}

function TaskPreview({ title, tasks }) {
  return (
    <section className="space-y-3" aria-label={title}>
      <h2 className="text-base font-semibold text-slate-900">{title}</h2>
      {tasks.length === 0 ? <EmptyState title={`No ${title.toLowerCase()}`} message="Nothing to show right now." /> : (
        <div className="space-y-2">{tasks.map((task) => (
          <TaskRow action={<StatusBadge value={task.task_status} />} key={task.id} showType task={task} />
        ))}</div>
      )}
    </section>
  );
}

function DashboardPage() {
  const [dashboard, setDashboard] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [actionError, setActionError] = useState(null);
  const requestVersion = useRef(0);
  const { markRead } = useNotifications();
  const navigate = useNavigate();

  const load = useCallback(async () => {
    const version = ++requestVersion.current;
    setLoading(true);
    setError(null);
    try {
      const data = await getDashboard(browserTimezone());
      if (version === requestVersion.current) setDashboard(data);
    } catch (apiError) {
      if (version === requestVersion.current) {
        setDashboard(null);
        setError(parseModule7Error(apiError));
      }
    } finally {
      if (version === requestVersion.current) setLoading(false);
    }
  }, []);

  useEffect(() => {
    load();
    return () => { requestVersion.current += 1; };
  }, [load]);

  async function openNotification(notification) {
    setActionError(null);
    try {
      if (!notification.is_read) await markRead(notification);
      navigate(notification.action_url);
    } catch (apiError) {
      setActionError(parseModule7Error(apiError));
    }
  }

  return (
    <div className="space-y-10">
      <section className="space-y-6" aria-label="Dashboard overview">
        <div className="flex flex-wrap items-end justify-between gap-3">
          <div>
            <p className="text-xs font-semibold uppercase tracking-wide text-cyan-700">At a glance</p>
            <h1 className="mt-1 text-2xl font-bold text-slate-900 sm:text-3xl">Dashboard</h1>
          </div>
          <Button disabled={loading} onClick={load}>Refresh dashboard</Button>
        </div>
        {loading ? <p className="text-sm text-slate-500" role="status">Loading dashboard summary...</p> : null}
        {error ? <div className="space-y-3"><Alert title="Could not load dashboard summary" {...error} /><Button onClick={load}>Try again</Button></div> : null}
        {actionError ? <Alert title="Notification action failed" {...actionError} /> : null}
        {!loading && dashboard ? (
          <>
            <div className="grid gap-3 sm:grid-cols-3">
              <SummaryCard label="Due today" value={dashboard.task_summary.due_today} />
              <SummaryCard label="Upcoming" value={dashboard.task_summary.upcoming} />
              <SummaryCard label="Overdue" value={dashboard.task_summary.overdue} />
            </div>
            <div className="grid gap-6 lg:grid-cols-3">
              <TaskPreview title="Tasks due today" tasks={dashboard.tasks_due_today} />
              <TaskPreview title="Upcoming tasks" tasks={dashboard.upcoming_tasks} />
              <TaskPreview title="Overdue tasks" tasks={dashboard.overdue_tasks} />
            </div>
            <div className="grid gap-6 lg:grid-cols-2">
              <section className="space-y-3" aria-label="Recent announcements">
                <h2 className="text-base font-semibold text-slate-900">Recent announcements</h2>
                {dashboard.recent_announcements.length === 0 ? <EmptyState title="No recent announcements" /> : dashboard.recent_announcements.map((item) => (
                  <article className="cf-card min-w-0 space-y-2 p-4" key={item.id}>
                    <Link className="block break-words text-sm font-semibold text-blue-700 hover:text-blue-900 cf-focus" to={item.action_url}>{item.title}</Link>
                    <p className="line-clamp-3 whitespace-pre-wrap break-words text-sm text-slate-600">{item.body}</p>
                    <time className="text-xs text-slate-500" dateTime={item.created_at}>{formatLocalDate(item.created_at)}</time>
                  </article>
                ))}
              </section>
              <section className="space-y-3" aria-label="Recent notifications">
                <div className="flex items-center justify-between gap-2">
                  <h2 className="text-base font-semibold text-slate-900">Recent notifications</h2>
                  <Link className="text-sm font-semibold text-blue-700 cf-focus" to="/notifications">View all</Link>
                </div>
                {dashboard.recent_notifications.length === 0 ? <EmptyState title="No recent notifications" /> : dashboard.recent_notifications.map((item) => (
                  <NotificationItem key={item.id} notification={item} onOpen={openNotification} />
                ))}
              </section>
            </div>
            {dashboard.pending_membership_request_count > 0 ? (
              <section className="space-y-3" aria-label="Pending membership requests">
                <h2 className="text-base font-semibold text-slate-900">Pending membership requests ({dashboard.pending_membership_request_count})</h2>
                {dashboard.pending_membership_requests.length === 0 ? <EmptyState title="No request previews" /> : (
                  <div className="grid gap-3 md:grid-cols-2">{dashboard.pending_membership_requests.map((request) => (
                    <div className="cf-card min-w-0 p-4" key={request.id}>
                      <Link className="break-words text-sm font-semibold text-blue-700 hover:text-blue-900 cf-focus" to={request.action_url}>
                        {request.user.first_name || request.user.username} · {request.classroom_name}
                      </Link>
                      <p className="mt-2 text-xs text-slate-500">Requested {formatLocalDate(request.requested_at)}</p>
                    </div>
                  ))}</div>
                )}
              </section>
            ) : null}
          </>
        ) : null}
      </section>
      <div className="border-t border-slate-200 pt-8">
        <h2 className="mb-5 text-lg font-semibold text-slate-900">Personal task feed</h2>
        <PersonalFeedPage />
      </div>
    </div>
  );
}

export default DashboardPage;
