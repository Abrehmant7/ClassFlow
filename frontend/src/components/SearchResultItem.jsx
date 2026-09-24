import { Link } from "react-router-dom";

import { formatLocalDate } from "../utils/module7.js";
import StatusBadge from "./StatusBadge.jsx";

const labels = { task: "Task", announcement: "Announcement", resource: "Resource" };

function SearchResultItem({ result }) {
  return (
    <article className="cf-card min-w-0 space-y-2 p-4">
      <StatusBadge value={result.entity_type} label={labels[result.entity_type] || "Content"} />
      <h2 className="break-words text-base font-semibold text-slate-900">
        <Link className="text-blue-700 hover:text-blue-900 cf-focus" to={result.action_url}>{result.title}</Link>
      </h2>
      {result.preview ? <p className="whitespace-pre-wrap break-words text-sm leading-6 text-slate-600">{result.preview}</p> : null}
      <div className="flex flex-wrap items-center gap-2 text-xs text-slate-500">
        {result.date ? <time dateTime={result.date}>{formatLocalDate(result.date)}</time> : null}
        {result.entity_type === "task" ? (
          <>
            {result.task_type ? <StatusBadge value={result.task_type} /> : null}
            {result.priority ? <StatusBadge value={result.priority} /> : null}
            {result.status ? <StatusBadge value={result.status} /> : null}
          </>
        ) : null}
      </div>
    </article>
  );
}

export default SearchResultItem;
