import { useCallback, useEffect, useMemo, useState } from "react";
import { Link, useParams } from "react-router-dom";

import { listMyClassrooms } from "../api/classrooms.js";
import { listClassCourses } from "../api/courses.js";
import {
  completePersonalTask,
  createTask,
  deleteTask,
  listTasks,
  reopenPersonalTask,
  updateTaskProgress,
} from "../api/tasks.js";
import Alert from "../components/Alert.jsx";
import Button from "../components/Button.jsx";
import ClassWorkspaceHeader from "../components/ClassWorkspaceHeader.jsx";
import EmptyState from "../components/EmptyState.jsx";
import FormField from "../components/FormField.jsx";
import LoadingScreen from "../components/LoadingScreen.jsx";
import Modal from "../components/Modal.jsx";
import TaskRow from "../components/TaskRow.jsx";
import TextAreaField from "../components/TextAreaField.jsx";
import { isApproved, isRepresentative } from "../utils/classrooms.js";
import { formatCourseTitle } from "../utils/courses.js";
import { parseApiError } from "../utils/errors.js";
import { TASK_PRIORITIES, TASK_TYPES, toApiDeadline } from "../utils/tasks.js";

const initialTaskForm = {
  title: "",
  description: "",
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

function isCompletedTask(task) {
  if (task.visibility === "personal") {
    return task.status === "completed";
  }

  return task.my_progress?.status === "completed";
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

function ClassTasksPage({ completedOnly = false }) {
  const { classId } = useParams();
  const numericClassId = Number(classId);
  const [classroom, setClassroom] = useState(null);
  const [membership, setMembership] = useState(null);
  const [tasks, setTasks] = useState([]);
  const [classCourses, setClassCourses] = useState([]);
  const [form, setForm] = useState(initialTaskForm);
  const [isCreateOpen, setIsCreateOpen] = useState(false);
  const [isLoading, setIsLoading] = useState(true);
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [actionKey, setActionKey] = useState("");
  const [error, setError] = useState(null);
  const [actionError, setActionError] = useState(null);
  const [success, setSuccess] = useState("");

  const canManageShared = useMemo(() => isRepresentative(membership), [membership]);
  const canViewTasks = useMemo(() => isApproved(membership), [membership]);

  const activeClassCourses = useMemo(
    () => classCourses.filter((classCourse) => classCourse.is_active),
    [classCourses],
  );

  const visibleTasks = useMemo(
    () =>
      tasks.filter((task) =>
        completedOnly ? isCompletedTask(task) : !isCompletedTask(task),
      ),
    [completedOnly, tasks],
  );

  const loadData = useCallback(async () => {
    setError(null);
    setActionError(null);

    try {
      const myClassrooms = await listMyClassrooms();
      const mineRecord = myClassrooms.find((item) => item.id === numericClassId);

      if (!mineRecord) {
        setClassroom(null);
        setMembership(null);
        setTasks([]);
        setError({ message: "This class is not in your memberships.", items: [] });
        return;
      }

      setClassroom(mineRecord);
      setMembership(mineRecord.membership);

      if (!isApproved(mineRecord.membership)) {
        setTasks([]);
        return;
      }

      const includeClosed = completedOnly && isRepresentative(mineRecord.membership);
      const [taskData, classCourseData] = await Promise.all([
        listTasks(numericClassId, includeClosed),
        listClassCourses(numericClassId),
      ]);
      setTasks(taskData);
      setClassCourses(classCourseData);
    } catch (apiError) {
      setError(parseApiError(apiError));
    }
  }, [completedOnly, numericClassId]);

  useEffect(() => {
    let isMounted = true;

    async function load() {
      await loadData();
      if (isMounted) {
        setIsLoading(false);
      }
    }

    load();

    return () => {
      isMounted = false;
    };
  }, [loadData]);

  function handleChange(event) {
    const { name, value } = event.target;
    setForm((current) => ({ ...current, [name]: value }));
  }

  async function handleSubmit(event) {
    event.preventDefault();
    setIsSubmitting(true);
    setActionError(null);
    setSuccess("");

    try {
      const payload = {
        title: form.title.trim(),
        visibility: "shared",
        task_type: form.task_type,
        priority: form.priority,
        class_course_id: form.class_course_id
          ? Number(form.class_course_id)
          : null,
        deadline: toApiDeadline(form.deadline),
      };

      const description = form.description.trim();
      if (description) {
        payload.description = description;
      }

      const created = await createTask(numericClassId, payload);
      setSuccess(`${created.title} was created.`);
      setForm(initialTaskForm);
      setIsCreateOpen(false);
      await loadData();
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
      setSuccess(message);
      await loadData();
    } catch (apiError) {
      setActionError(parseApiError(apiError));
    } finally {
      setActionKey("");
    }
  }

  if (isLoading) {
    return <LoadingScreen message="Loading tasks..." />;
  }

  if (error && !classroom) {
    return (
      <section className="space-y-5">
        <Alert title="Could not load tasks" message={error.message} items={error.items} />
        <Link
          className="inline-flex rounded-lg bg-blue-600 px-4 py-2 text-sm font-semibold text-white hover:bg-blue-700 cf-focus"
          to="/classes"
        >
          Back to classes
        </Link>
      </section>
    );
  }

  return (
    <section className="space-y-6">
      <ClassWorkspaceHeader
        actions={
          canManageShared && !completedOnly ? (
            <Button onClick={() => setIsCreateOpen(true)} variant="primary">
              Create shared task
            </Button>
          ) : null
        }
        classroom={classroom}
        membership={membership}
      />

      {error ? (
        <Alert title="Task access blocked" message={error.message} items={error.items} />
      ) : null}

      {!canViewTasks ? (
        <Alert
          message="Tasks are available after a representative approves your class membership."
          title={`Membership ${membership?.status}`}
          type="warning"
        />
      ) : (
        <>
          {actionError ? (
            <Alert
              title="Task action failed"
              message={actionError.message}
              items={actionError.items}
            />
          ) : null}
          {success ? (
            <Alert type="success" title="Updated" message={success} />
          ) : null}

          <div className="flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-between">
            <div className="inline-flex rounded-lg bg-slate-100 p-1">
              <Link
                className={`rounded-md px-3 py-1.5 text-sm font-semibold transition cf-focus ${
                  !completedOnly
                    ? "bg-white text-blue-700 shadow-sm"
                    : "text-slate-600 hover:text-slate-900"
                }`}
                to={`/classes/${numericClassId}/tasks`}
              >
                Pending
              </Link>
              <Link
                className={`rounded-md px-3 py-1.5 text-sm font-semibold transition cf-focus ${
                  completedOnly
                    ? "bg-white text-blue-700 shadow-sm"
                    : "text-slate-600 hover:text-slate-900"
                }`}
                to={`/classes/${numericClassId}/completed-tasks`}
              >
                Completed
              </Link>
            </div>
            <span className="text-sm text-slate-500">
              {visibleTasks.length} {completedOnly ? "completed" : "pending"}
            </span>
          </div>

          {visibleTasks.length === 0 ? (
            <EmptyState
              action={
                canManageShared && !completedOnly ? (
                  <Button onClick={() => setIsCreateOpen(true)} variant="primary">
                    Create shared task
                  </Button>
                ) : null
              }
              message={
                completedOnly
                  ? "Completed tasks will appear here after you mark work done."
                  : "No pending shared tasks are currently visible for this class."
              }
              title={completedOnly ? "No completed tasks" : "No pending tasks"}
            />
          ) : (
            <div className="space-y-2">
              {visibleTasks.map((task) => {
                const isPersonal = task.visibility === "personal";
                const completed = isCompletedTask(task);
                const isBusy = actionKey?.endsWith(`:${task.id}`);

                return (
                  <TaskRow
                    key={task.id}
                    menu={
                      task.can_manage && isPersonal ? (
                        <Button
                          className="px-3 py-1.5"
                          onClick={() => {
                            if (window.confirm("Delete this personal task?")) {
                              runAction(
                                `delete:${task.id}`,
                                () => deleteTask(task.id),
                                "Task deleted.",
                              );
                            }
                          }}
                          variant="danger"
                        >
                          Delete
                        </Button>
                      ) : null
                    }
                    progressControl={
                      <TaskProgressButton
                        checked={completed}
                        disabled={!isPersonal && !task.can_manage && false}
                        isBusy={isBusy}
                        onClick={() =>
                          isPersonal
                            ? runAction(
                                `${completed ? "reopen" : "complete"}:${task.id}`,
                                () =>
                                  completed
                                    ? reopenPersonalTask(task.id)
                                    : completePersonalTask(task.id),
                                completed
                                  ? "Personal task reopened."
                                  : "Personal task completed.",
                              )
                            : runAction(
                                `progress:${task.id}`,
                                () =>
                                  updateTaskProgress(
                                    task.id,
                                    completed ? "pending" : "completed",
                                  ),
                                completed
                                  ? "Shared task marked pending."
                                  : "Shared task marked complete.",
                              )
                        }
                      />
                    }
                    showType
                    task={task}
                  />
                );
              })}
            </div>
          )}
        </>
      )}

      <Modal
        description="Shared tasks are visible to approved members according to the backend course and membership rules."
        isOpen={isCreateOpen}
        onClose={() => setIsCreateOpen(false)}
        title="Create shared task"
      >
        <form className="space-y-4" onSubmit={handleSubmit}>
          <FormField
            id="task-title"
            label="Title"
            name="title"
            onChange={handleChange}
            required
            value={form.title}
          />
          <div className="grid gap-4 sm:grid-cols-2">
            <SelectField
              id="task-course"
              label="Course"
              name="class_course_id"
              onChange={handleChange}
              value={form.class_course_id}
            >
              <option value="">Class-wide</option>
              {activeClassCourses.map((classCourse) => (
                <option key={classCourse.id} value={classCourse.id}>
                  {formatCourseTitle(classCourse.course)}
                </option>
              ))}
            </SelectField>
            <SelectField
              id="task-priority"
              label="Priority"
              name="priority"
              onChange={handleChange}
              value={form.priority}
            >
              {TASK_PRIORITIES.map((priority) => (
                <option key={priority} value={priority}>
                  {priority}
                </option>
              ))}
            </SelectField>
            <SelectField
              id="task-type"
              label="Task type"
              name="task_type"
              onChange={handleChange}
              value={form.task_type}
            >
              {TASK_TYPES.map((type) => (
                <option key={type} value={type}>
                  {type}
                </option>
              ))}
            </SelectField>
            <FormField
              id="task-deadline"
              label="Deadline"
              name="deadline"
              onChange={handleChange}
              type="datetime-local"
              value={form.deadline}
            />
          </div>
          <TextAreaField
            id="task-description"
            label="Description"
            name="description"
            onChange={handleChange}
            rows={3}
            value={form.description}
          />
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

export default ClassTasksPage;
