import { useCallback, useEffect, useMemo, useState } from "react";
import { Link, useSearchParams } from "react-router-dom";

import {
  fetchFeed,
  fetchFeedFilterOptions,
  fetchFeedSummary,
} from "../api/feed.js";
import {
  completePersonalTask,
  createPersonalTask,
  deleteTask,
  reopenPersonalTask,
  updateTaskProgress,
} from "../api/tasks.js";
import Alert from "../components/Alert.jsx";
import Button from "../components/Button.jsx";
import EmptyState from "../components/EmptyState.jsx";
import FormField from "../components/FormField.jsx";
import LoadingScreen from "../components/LoadingScreen.jsx";
import Modal from "../components/Modal.jsx";
import TaskRow from "../components/TaskRow.jsx";
import TextAreaField from "../components/TextAreaField.jsx";
import { useAuth } from "../auth/useAuth.js";
import { parseApiError } from "../utils/errors.js";
import {
  TASK_PRIORITIES,
  TASK_TYPES,
  toApiDeadline,
} from "../utils/tasks.js";
import { getDisplayName } from "../utils/user.js";

const pageSize = 20;
const timezone = "UTC";

const defaultFilters = {
  view: "active",
  visibility: "all",
  classroom_id: "",
  class_course_id: "",
  task_type: "",
  priority: "",
  due: "",
  search: "",
};

const initialTaskForm = {
  title: "",
  description: "",
  classroom_id: "",
  class_course_id: "",
  task_type: "other",
  priority: "medium",
  deadline: "",
};

function SelectField({ id, label, name, onChange, value, children }) {
  return (
    <div>
      <label htmlFor={id} className="cf-label">
        {label}
      </label>
      <select
        className="cf-input"
        id={id}
        name={name}
        onChange={onChange}
        value={value}
      >
        {children}
      </select>
    </div>
  );
}

function readFilters(searchParams) {
  return {
    ...defaultFilters,
    view: searchParams.get("view") || defaultFilters.view,
    visibility: searchParams.get("visibility") || defaultFilters.visibility,
    classroom_id: searchParams.get("classroom_id") || "",
    class_course_id: searchParams.get("class_course_id") || "",
    task_type: searchParams.get("task_type") || "",
    priority: searchParams.get("priority") || "",
    due: searchParams.get("due") || "",
    search: searchParams.get("search") || "",
  };
}

function getPage(searchParams) {
  const page = Number(searchParams.get("page") || 1);
  return Number.isFinite(page) && page > 0 ? page : 1;
}

function SummaryStrip({ onApplyDue, summary }) {
  const items = [
    ["Overdue", summary?.overdue ?? 0, "overdue"],
    ["Due today", summary?.due_today ?? 0, "today"],
    ["Next seven days", summary?.upcoming_seven_days ?? 0, "week"],
    ["Completed this week", summary?.completed_this_week ?? 0, "completed"],
  ];

  return (
    <div className="grid overflow-hidden rounded-lg border border-slate-200 bg-white shadow-sm sm:grid-cols-2 lg:grid-cols-4">
      {items.map(([label, value, due], index) => (
        <button
          className={`px-4 py-3 text-left transition hover:bg-slate-50 cf-focus ${
            index > 0 ? "border-t border-slate-200 sm:border-l sm:border-t-0" : ""
          }`}
          key={label}
          onClick={() => onApplyDue(due)}
          type="button"
        >
          <p className="text-xs font-semibold uppercase tracking-wide text-slate-500">
            {label}
          </p>
          <p className="mt-1 text-2xl font-bold tabular-nums text-slate-900">
            {value}
          </p>
        </button>
      ))}
    </div>
  );
}

function FilterChip({ label, onRemove }) {
  return (
    <span className="inline-flex items-center gap-1 rounded-full bg-slate-100 px-2.5 py-1 text-xs font-medium text-slate-700">
      {label}
      <button
        aria-label={`Remove ${label} filter`}
        className="rounded-full px-1 text-slate-500 hover:bg-white hover:text-slate-900 cf-focus"
        onClick={onRemove}
        type="button"
      >
        x
      </button>
    </span>
  );
}

function TaskProgressButton({ checked, disabled, isBusy, onClick }) {
  return (
    <button
      aria-pressed={checked}
      className={`flex h-5 w-5 items-center justify-center rounded border text-xs font-bold transition cf-focus ${
        checked
          ? "border-emerald-600 bg-emerald-600 text-white"
          : "border-slate-300 bg-white text-transparent hover:border-blue-600"
      } disabled:cursor-not-allowed disabled:opacity-60`}
      disabled={disabled || isBusy}
      onClick={onClick}
      type="button"
    >
      Ã¢Å“â€œ
    </button>
  );
}

function RowMenu({ canDelete, canEdit, isBusy, onDelete, task }) {
  if (!canEdit && !canDelete) return null;

  return (
    <details className="relative">
      <summary className="list-none rounded-lg border border-slate-200 px-3 py-1.5 text-sm font-semibold text-slate-600 transition hover:bg-slate-50 cf-focus">
        More
      </summary>
      <div className="absolute right-0 z-10 mt-2 w-40 rounded-lg border border-slate-200 bg-white p-1 shadow-lg">
        {canEdit ? (
          <Link
            className="block rounded-md px-3 py-2 text-sm font-medium text-slate-700 hover:bg-slate-50 cf-focus"
            to={`/tasks/${task.id}`}
          >
            Edit details
          </Link>
        ) : null}
        {canDelete ? (
          <button
            className="block w-full rounded-md px-3 py-2 text-left text-sm font-medium text-red-600 hover:bg-red-50 cf-focus disabled:opacity-60"
            disabled={isBusy}
            onClick={onDelete}
            type="button"
          >
            {isBusy ? "Deleting..." : "Delete"}
          </button>
        ) : null}
      </div>
    </details>
  );
}

function TaskSection({ actionKey, onDelete, onPersonalToggle, onSharedToggle, tasks, title }) {
  if (tasks.length === 0) return null;

  return (
    <section className="space-y-2">
      <div className="flex items-center gap-2">
        <h2 className="text-sm font-semibold text-slate-900">{title}</h2>
        <span className="text-xs text-slate-500">{tasks.length}</span>
      </div>
      <div className="space-y-2">
        {tasks.map((task) => {
          const isPersonal = task.visibility === "personal";
          const isCompleted = task.my_completion_status === "completed";
          const isBusy = actionKey?.endsWith(`:${task.id}`);

          return (
            <TaskRow
              key={task.id}
              menu={
                <RowMenu
                  canDelete={task.permissions.can_delete}
                  canEdit={task.permissions.can_edit}
                  isBusy={isBusy}
                  onDelete={() => {
                    if (window.confirm("Delete this task?")) {
                      onDelete(task.id);
                    }
                  }}
                  task={task}
                />
              }
              progressControl={
                <TaskProgressButton
                  checked={isCompleted}
                  disabled={
                    isPersonal
                      ? task.task_status === "archived"
                      : !task.permissions.can_update_progress
                  }
                  isBusy={isBusy}
                  onClick={() =>
                    isPersonal
                      ? onPersonalToggle(task)
                      : onSharedToggle(task, isCompleted ? "pending" : "completed")
                  }
                />
              }
              showType
              task={task}
            />
          );
        })}
      </div>
    </section>
  );
}

function groupTasks(tasks, view) {
  if (view === "completed") {
    return [["Completed", tasks]];
  }

  const labels = {
    overdue: "Overdue",
    today: "Today",
    upcoming: "Upcoming",
    later: "Later",
    no_deadline: "No deadline",
  };

  return Object.entries(labels).map(([key, label]) => [
    label,
    tasks.filter((task) => task.due_group === key),
  ]);
}

function PersonalFeedPage() {
  const { user } = useAuth();
  const [searchParams, setSearchParams] = useSearchParams();
  const filters = useMemo(() => readFilters(searchParams), [searchParams]);
  const page = useMemo(() => getPage(searchParams), [searchParams]);
  const [summary, setSummary] = useState(null);
  const [options, setOptions] = useState({ classrooms: [], courses: [] });
  const [feed, setFeed] = useState({
    items: [],
    page: 1,
    page_size: pageSize,
    total: 0,
    total_pages: 0,
  });
  const [form, setForm] = useState(initialTaskForm);
  const [showFilters, setShowFilters] = useState(false);
  const [showMoreOptions, setShowMoreOptions] = useState(false);
  const [isCreateOpen, setIsCreateOpen] = useState(false);
  const [isLoading, setIsLoading] = useState(true);
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [actionKey, setActionKey] = useState("");
  const [error, setError] = useState(null);
  const [actionError, setActionError] = useState(null);
  const [success, setSuccess] = useState("");

  const createCourseOptions = useMemo(() => {
    if (!form.classroom_id) return [];
    return options.courses.filter(
      (course) => course.classroom_id === Number(form.classroom_id),
    );
  }, [form.classroom_id, options.courses]);

  const courseFilterOptions = useMemo(() => {
    if (!filters.classroom_id) return options.courses;
    return options.courses.filter(
      (course) => course.classroom_id === Number(filters.classroom_id),
    );
  }, [filters.classroom_id, options.courses]);

  const updateParams = useCallback(
    (updates) => {
      const next = new URLSearchParams(searchParams);

      Object.entries(updates).forEach(([key, value]) => {
        if (!value || value === defaultFilters[key]) {
          next.delete(key);
        } else {
          next.set(key, String(value));
        }
      });

      if (!Object.prototype.hasOwnProperty.call(updates, "page")) {
        next.delete("page");
      }

      setSearchParams(next);
    },
    [searchParams, setSearchParams],
  );

  const loadFeed = useCallback(async () => {
    setError(null);
    setActionError(null);

    try {
      const params = {
        ...filters,
        search: filters.search.trim().slice(0, 100),
        timezone,
        page,
        page_size: pageSize,
      };

      if (!params.search) {
        delete params.search;
      }

      const [summaryData, feedData] = await Promise.all([
        fetchFeedSummary(timezone),
        fetchFeed(params),
      ]);
      setSummary(summaryData);
      setFeed(feedData);
    } catch (apiError) {
      setError(parseApiError(apiError));
    }
  }, [filters, page]);

  useEffect(() => {
    let isMounted = true;

    async function loadInitial() {
      try {
        const filterOptions = await fetchFeedFilterOptions();
        if (isMounted) {
          setOptions(filterOptions);
        }
      } catch (apiError) {
        if (isMounted) {
          setError(parseApiError(apiError));
        }
      }

      await loadFeed();
      if (isMounted) {
        setIsLoading(false);
      }
    }

    loadInitial();

    return () => {
      isMounted = false;
    };
  }, [loadFeed]);

  useEffect(() => {
    if (searchParams.get("newTask") === "1") {
      setIsCreateOpen(true);
      const next = new URLSearchParams(searchParams);
      next.delete("newTask");
      setSearchParams(next, { replace: true });
    }
  }, [searchParams, setSearchParams]);

  function updateFilter(name, value) {
    updateParams({
      [name]: value.slice ? value.slice(0, 100) : value,
      ...(name === "classroom_id" ? { class_course_id: "" } : {}),
    });
  }

  function clearFilters() {
    setSearchParams(new URLSearchParams());
  }

  function handleFormChange(event) {
    const { name, value } = event.target;
    setForm((current) => ({
      ...current,
      [name]: value,
      ...(name === "classroom_id" ? { class_course_id: "" } : {}),
    }));
  }

  async function refreshAfterAction(message) {
    setSuccess(message);
    await loadFeed();
  }

  async function handleCreate(event) {
    event.preventDefault();
    setIsSubmitting(true);
    setActionError(null);
    setSuccess("");

    try {
      const payload = {
        title: form.title.trim(),
        task_type: form.task_type,
        priority: form.priority,
        deadline: toApiDeadline(form.deadline),
        classroom_id: form.classroom_id ? Number(form.classroom_id) : null,
        class_course_id: form.class_course_id
          ? Number(form.class_course_id)
          : null,
      };

      const description = form.description.trim();
      if (description) {
        payload.description = description;
      }

      const created = await createPersonalTask(payload);
      setForm(initialTaskForm);
      setIsCreateOpen(false);
      setShowMoreOptions(false);
      await refreshAfterAction(`${created.title} was created.`);
    } catch (apiError) {
      setActionError(parseApiError(apiError));
    } finally {
      setIsSubmitting(false);
    }
  }

  async function runAction(key, action, message) {
    setActionKey(key);
    setActionError(null);
    setSuccess("");

    try {
      await action();
      await refreshAfterAction(message);
    } catch (apiError) {
      setActionError(parseApiError(apiError));
    } finally {
      setActionKey("");
    }
  }

  const activeFilterEntries = Object.entries(filters).filter(
    ([key, value]) => key !== "view" && value && value !== defaultFilters[key],
  );
  const taskGroups = groupTasks(feed.items, filters.view);

  if (isLoading) {
    return <LoadingScreen message="Loading dashboard..." />;
  }

  return (
    <section className="space-y-6">
      <div className="flex flex-col gap-4 sm:flex-row sm:items-end sm:justify-between">
        <div>
          <p className="text-sm font-semibold text-cyan-700">
            Good morning, {getDisplayName(user).split(" ")[0]}
          </p>
          <h1 className="mt-1 text-2xl font-bold tracking-tight text-slate-900 sm:text-3xl">
            Here&apos;s what needs your attention.
          </h1>
        </div>
        <Button onClick={() => setIsCreateOpen(true)} variant="primary">
          New personal task
        </Button>
      </div>

      {error ? (
        <Alert title="Could not load dashboard" message={error.message} items={error.items} />
      ) : null}
      {actionError ? (
        <Alert
          title="Task action failed"
          message={actionError.message}
          items={actionError.items}
        />
      ) : null}
      {success ? <Alert type="success" title="Updated" message={success} /> : null}

      <SummaryStrip
        onApplyDue={(due) => {
          if (due === "completed") {
            updateParams({ view: "completed", due: "" });
          } else {
            updateParams({ view: "active", due });
          }
        }}
        summary={summary}
      />

      <div className="cf-card p-3">
        <div className="flex flex-col gap-3 lg:flex-row lg:items-center">
          <div className="flex-1">
            <label className="sr-only" htmlFor="feed-search">
              Search tasks
            </label>
            <input
              className="block w-full rounded-lg border border-slate-300 bg-white px-3 py-2 text-sm text-slate-900 shadow-sm outline-none transition placeholder:text-slate-400 focus:border-blue-600 focus:ring-2 focus:ring-blue-600/20"
              id="feed-search"
              onChange={(event) => updateFilter("search", event.target.value)}
              placeholder="Search tasks"
              value={filters.search}
            />
          </div>

          <div className="inline-flex rounded-lg bg-slate-100 p-1">
            {["active", "completed"].map((view) => (
              <button
                className={`rounded-md px-3 py-1.5 text-sm font-semibold transition cf-focus ${
                  filters.view === view
                    ? "bg-white text-blue-700 shadow-sm"
                    : "text-slate-600 hover:text-slate-900"
                }`}
                key={view}
                onClick={() => updateParams({ view, due: "" })}
                type="button"
              >
                {view}
              </button>
            ))}
          </div>

          <Button onClick={() => setShowFilters((current) => !current)}>
            Filters
          </Button>
        </div>

        {showFilters ? (
          <div className="mt-4 grid gap-4 border-t border-slate-200 pt-4 md:grid-cols-2 xl:grid-cols-3">
            <SelectField
              id="feed-visibility"
              label="Visibility"
              name="visibility"
              onChange={(event) => updateFilter("visibility", event.target.value)}
              value={filters.visibility}
            >
              <option value="all">All</option>
              <option value="personal">Personal</option>
              <option value="shared">Shared</option>
            </SelectField>
            <SelectField
              id="feed-classroom"
              label="Classroom"
              name="classroom_id"
              onChange={(event) => updateFilter("classroom_id", event.target.value)}
              value={filters.classroom_id}
            >
              <option value="">All classrooms</option>
              {options.classrooms.map((classroom) => (
                <option key={classroom.id} value={classroom.id}>
                  {classroom.name}
                </option>
              ))}
            </SelectField>
            <SelectField
              id="feed-course"
              label="Course"
              name="class_course_id"
              onChange={(event) =>
                updateFilter("class_course_id", event.target.value)
              }
              value={filters.class_course_id}
            >
              <option value="">All courses</option>
              {courseFilterOptions.map((course) => (
                <option key={course.class_course_id} value={course.class_course_id}>
                  {course.code} / {course.name}
                </option>
              ))}
            </SelectField>
            <SelectField
              id="feed-type"
              label="Task type"
              name="task_type"
              onChange={(event) => updateFilter("task_type", event.target.value)}
              value={filters.task_type}
            >
              <option value="">All types</option>
              {TASK_TYPES.map((type) => (
                <option key={type} value={type}>
                  {type}
                </option>
              ))}
            </SelectField>
            <SelectField
              id="feed-priority"
              label="Priority"
              name="priority"
              onChange={(event) => updateFilter("priority", event.target.value)}
              value={filters.priority}
            >
              <option value="">All priorities</option>
              {TASK_PRIORITIES.map((priority) => (
                <option key={priority} value={priority}>
                  {priority}
                </option>
              ))}
            </SelectField>
            <SelectField
              id="feed-due"
              label="Due period"
              name="due"
              onChange={(event) => updateFilter("due", event.target.value)}
              value={filters.due}
            >
              <option value="">Any due date</option>
              <option value="overdue">Overdue</option>
              <option value="today">Today</option>
              <option value="week">Next seven days</option>
              <option value="later">Later</option>
              <option value="no_deadline">No deadline</option>
            </SelectField>
          </div>
        ) : null}

        {activeFilterEntries.length > 0 ? (
          <div className="mt-3 flex flex-wrap items-center gap-2">
            {activeFilterEntries.map(([key, value]) => (
              <FilterChip
                key={key}
                label={`${key.replaceAll("_", " ")}: ${value}`}
                onRemove={() => updateFilter(key, "")}
              />
            ))}
            <button
              className="text-xs font-semibold text-blue-700 hover:text-blue-900 cf-focus"
              onClick={clearFilters}
              type="button"
            >
              Clear all
            </button>
          </div>
        ) : null}
      </div>

      <div className="flex items-center justify-between">
        <h2 className="text-base font-semibold text-slate-900">Tasks</h2>
        <span className="text-sm text-slate-500">{feed.total} total</span>
      </div>

      {feed.items.length === 0 ? (
        <EmptyState
          action={
            filters.search || activeFilterEntries.length > 0 ? (
              <Button onClick={clearFilters}>Clear filters</Button>
            ) : (
              <Button onClick={() => setIsCreateOpen(true)} variant="primary">
                New personal task
              </Button>
            )
          }
          message={
            filters.search || activeFilterEntries.length > 0
              ? "Try clearing a filter or changing the search."
              : "Create a personal task or check back when shared class tasks are assigned."
          }
          title={
            filters.search || activeFilterEntries.length > 0
              ? "No matching tasks"
              : "No tasks yet"
          }
        />
      ) : (
        <div className="space-y-5">
          {taskGroups.map(([title, tasks]) => (
            <TaskSection
              actionKey={actionKey}
              key={title}
              onDelete={(taskId) =>
                runAction(
                  `delete:${taskId}`,
                  () => deleteTask(taskId),
                  "Task deleted.",
                )
              }
              onPersonalToggle={(task) =>
                runAction(
                  `${task.task_status === "completed" ? "reopen" : "complete"}:${task.id}`,
                  () =>
                    task.task_status === "completed"
                      ? reopenPersonalTask(task.id)
                      : completePersonalTask(task.id),
                  task.task_status === "completed"
                    ? "Personal task reopened."
                    : "Personal task completed.",
                )
              }
              onSharedToggle={(task, status) =>
                runAction(
                  `progress:${task.id}`,
                  () => updateTaskProgress(task.id, status),
                  status === "completed"
                    ? "Shared task marked complete."
                    : "Shared task marked pending.",
                )
              }
              tasks={tasks}
              title={title}
            />
          ))}
        </div>
      )}

      <div className="flex items-center justify-between">
        <Button
          disabled={page <= 1}
          onClick={() => updateParams({ page: Math.max(1, page - 1) })}
        >
          Previous
        </Button>
        <span className="text-sm text-slate-500">
          Page {feed.page} of {feed.total_pages || 1}
        </span>
        <Button
          disabled={feed.total_pages === 0 || page >= feed.total_pages}
          onClick={() => updateParams({ page: page + 1 })}
        >
          Next
        </Button>
      </div>

      <Modal
        description="Start with the essentials. Classroom and course links are optional."
        isOpen={isCreateOpen}
        onClose={() => setIsCreateOpen(false)}
        title="New personal task"
      >
        <form className="space-y-4" onSubmit={handleCreate}>
          <div className="grid gap-4 sm:grid-cols-3">
            <div className="sm:col-span-3">
              <FormField
                id="feed-task-title"
                label="Title"
                name="title"
                onChange={handleFormChange}
                required
                value={form.title}
              />
            </div>
            <FormField
              id="feed-task-deadline"
              label="Deadline"
              name="deadline"
              onChange={handleFormChange}
              type="datetime-local"
              value={form.deadline}
            />
            <SelectField
              id="feed-task-priority"
              label="Priority"
              name="priority"
              onChange={handleFormChange}
              value={form.priority}
            >
              {TASK_PRIORITIES.map((priority) => (
                <option key={priority} value={priority}>
                  {priority}
                </option>
              ))}
            </SelectField>
          </div>

          <button
            className="text-sm font-semibold text-blue-700 hover:text-blue-900 cf-focus"
            onClick={() => setShowMoreOptions((current) => !current)}
            type="button"
          >
            {showMoreOptions ? "Hide more options" : "More options"}
          </button>

          {showMoreOptions ? (
            <div className="space-y-4 rounded-lg border border-slate-200 bg-slate-50 p-4">
              <TextAreaField
                id="feed-task-description"
                label="Description"
                name="description"
                onChange={handleFormChange}
                rows={3}
                value={form.description}
              />
              <div className="grid gap-4 sm:grid-cols-2">
                <SelectField
                  id="feed-task-type"
                  label="Task type"
                  name="task_type"
                  onChange={handleFormChange}
                  value={form.task_type}
                >
                  {TASK_TYPES.map((type) => (
                    <option key={type} value={type}>
                      {type}
                    </option>
                  ))}
                </SelectField>
                <SelectField
                  id="feed-task-classroom"
                  label="Related classroom"
                  name="classroom_id"
                  onChange={handleFormChange}
                  value={form.classroom_id}
                >
                  <option value="">No classroom</option>
                  {options.classrooms.map((classroom) => (
                    <option key={classroom.id} value={classroom.id}>
                      {classroom.name}
                    </option>
                  ))}
                </SelectField>
                {form.classroom_id ? (
                  <SelectField
                    id="feed-task-course"
                    label="Related course"
                    name="class_course_id"
                    onChange={handleFormChange}
                    value={form.class_course_id}
                  >
                    <option value="">No course</option>
                    {createCourseOptions.map((course) => (
                      <option
                        key={course.class_course_id}
                        value={course.class_course_id}
                      >
                        {course.code} / {course.name}
                      </option>
                    ))}
                  </SelectField>
                ) : null}
              </div>
              <p className="text-xs text-slate-500">
                Attachments can be added from the task detail page after the task
                is created.
              </p>
            </div>
          ) : null}

          {actionError ? (
            <Alert
              title="Could not create task"
              message={actionError.message}
              items={actionError.items}
            />
          ) : null}

          <div className="flex flex-col-reverse gap-2 sm:flex-row sm:justify-end">
            <Button onClick={() => setIsCreateOpen(false)}>Cancel</Button>
            <Button disabled={isSubmitting} type="submit" variant="primary">
              {isSubmitting ? "Creating..." : "Create task"}
            </Button>
          </div>
        </form>
      </Modal>
    </section>
  );
}

export default PersonalFeedPage;
