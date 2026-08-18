import { Link } from "react-router-dom";

import StatusBadge from "./StatusBadge.jsx";
import { formatDeadline } from "../utils/tasks.js";

function getContext(task) {
  if (task.course) {
    return task.course.code
      ? `${task.course.code} / ${task.course.name}`
      : task.course.name;
  }

  if (task.classroom?.name) {
    return task.classroom.name;
  }

  return "";
}

function TaskRow({
  action,
  menu,
  progressControl,
  showType = false,
  task,
}) {
  const context = getContext(task);
  const title = task.title;
  const priority = task.priority && task.priority !== "medium" ? task.priority : null;
  const type = showType && task.task_type && task.task_type !== "other" ? task.task_type : null;
  const attachmentCount = task.attachment_count ?? task.attachments?.length ?? 0;

  return (
    <div className="group grid gap-3 rounded-lg border border-slate-200 bg-white px-4 py-3 shadow-sm transition duration-150 hover:-translate-y-0.5 hover:border-slate-300 hover:shadow-md active:translate-y-0 active:shadow-sm sm:grid-cols-[auto_1fr_auto] sm:items-center">
      <div className="flex items-start gap-3 sm:contents">
        {progressControl ? (
          <div className="pt-0.5 sm:pt-0">{progressControl}</div>
        ) : null}
        <div className="min-w-0">
          <Link
            className="block truncate rounded text-sm font-semibold text-slate-900 transition hover:text-blue-700 focus-visible:text-blue-700 cf-focus"
            to={`/tasks/${task.id}`}
          >
            {title}
          </Link>
          <div className="mt-1 flex flex-wrap items-center gap-x-2 gap-y-1 text-xs text-slate-500">
            {context ? <span>{context}</span> : null}
            {context ? <span aria-hidden="true">/</span> : null}
            <span>{formatDeadline(task.deadline)}</span>
            {attachmentCount > 0 ? (
              <>
                <span aria-hidden="true">/</span>
                <span>{attachmentCount} attachment{attachmentCount === 1 ? "" : "s"}</span>
              </>
            ) : null}
          </div>
        </div>
      </div>

      <div className="flex flex-wrap items-center gap-2 sm:justify-end">
        <StatusBadge value={task.visibility} subtle={task.visibility === "shared"} />
        {priority ? <StatusBadge value={priority} /> : null}
        {type ? <StatusBadge value={type} subtle /> : null}
        {action}
        {menu}
      </div>
    </div>
  );
}

export default TaskRow;
