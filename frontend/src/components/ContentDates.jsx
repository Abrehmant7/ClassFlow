import { formatDeadline } from "../utils/tasks.js";

function ContentDates({ createdAt, updatedAt }) {
  return (
    <p className="text-xs leading-5 text-slate-500">
      Created <time dateTime={createdAt}>{formatDeadline(createdAt)}</time>
      {updatedAt && new Date(updatedAt).getTime() !== new Date(createdAt).getTime() ? (
        <> · Updated <time dateTime={updatedAt}>{formatDeadline(updatedAt)}</time></>
      ) : null}
    </p>
  );
}

export default ContentDates;
