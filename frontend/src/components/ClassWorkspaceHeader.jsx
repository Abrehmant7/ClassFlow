import StatusBadge from "./StatusBadge.jsx";
import Tabs from "./Tabs.jsx";
import { isRepresentative } from "../utils/classrooms.js";

function ClassWorkspaceHeader({ classroom, membership, actions }) {
  const classId = classroom?.id;
  const tabs = classId
    ? [
        { label: "Overview", to: `/classes/${classId}`, end: true },
        { label: "Tasks", to: `/classes/${classId}/tasks` },
        { label: "Courses", to: `/classes/${classId}/courses` },
        { label: "Members", to: `/classes/${classId}/members` },
      ]
    : [];

  return (
    <div className="space-y-4">
      <div className="flex flex-col gap-4 sm:flex-row sm:items-end sm:justify-between">
        <div>
          <p className="text-xs font-semibold uppercase tracking-wide text-cyan-700">
            Classroom
          </p>
          <h1 className="mt-1 text-2xl font-bold tracking-tight text-slate-900 sm:text-3xl">
            {classroom?.name || "Class"}
          </h1>
          {classroom ? (
            <div className="mt-2 flex flex-wrap items-center gap-2 text-sm text-slate-500">
              <span>Semester {classroom.semester}</span>
              <span aria-hidden="true">/</span>
              <span>Section {classroom.section}</span>
              <StatusBadge value={membership?.role} subtle={!isRepresentative(membership)} />
              {membership?.status !== "approved" ? (
                <StatusBadge value={membership?.status} />
              ) : null}
            </div>
          ) : null}
        </div>
        {actions ? <div className="flex flex-wrap gap-2">{actions}</div> : null}
      </div>
      {tabs.length > 0 ? <Tabs items={tabs} /> : null}
    </div>
  );
}

export default ClassWorkspaceHeader;
