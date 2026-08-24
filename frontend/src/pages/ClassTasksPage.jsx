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
import LoadingScreen from "../components/LoadingScreen.jsx";
import Modal from "../components/Modal.jsx";
import SharedTaskModal from "../components/SharedTaskModal.jsx";
import TaskProgressButton from "../components/TaskProgressButton.jsx";
import TaskRow from "../components/TaskRow.jsx";
import { isApproved, isRepresentative } from "../utils/classrooms.js";
import { parseApiError } from "../utils/errors.js";

function isCompletedTask(task) {
  if (task.visibility === "personal") {
    return task.status === "completed";
  }

  return task.my_progress?.status === "completed";
}

function ClassTasksPage({ completedOnly = false }) {
  const { classId } = useParams();
  const numericClassId = Number(classId);
  const [classroom, setClassroom] = useState(null);
  const [membership, setMembership] = useState(null);
  const [tasks, setTasks] = useState([]);
  const [classCourses, setClassCourses] = useState([]);
  const [isCreateOpen, setIsCreateOpen] = useState(false);
  const [deleteCandidate, setDeleteCandidate] = useState(null);
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

  async function handleCreateSharedTask(payload) {
    setIsSubmitting(true);
    setActionError(null);
    setSuccess("");

    try {
      const created = await createTask(numericClassId, payload);
      setSuccess(`${created.title} was created.`);
      await loadData();
      return created;
    } catch (apiError) {
      setActionError(parseApiError(apiError));
      return null;
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
                          onClick={() => setDeleteCandidate(task)}
                          variant="danger"
                        >
                          Delete
                        </Button>
                      ) : null
                    }
                    progressControl={
                      <TaskProgressButton
                        checked={completed}
                        disabled={task.status !== "active"}
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

      <SharedTaskModal
        activeClassCourses={activeClassCourses}
        error={actionError}
        isOpen={isCreateOpen}
        isSubmitting={isSubmitting}
        onClose={() => {
          setIsCreateOpen(false);
          setActionError(null);
        }}
        onCreate={handleCreateSharedTask}
      />

      <Modal
        description="This removes the personal task from this class view."
        isOpen={Boolean(deleteCandidate)}
        onClose={() => setDeleteCandidate(null)}
        title="Delete personal task?"
      >
        <div className="space-y-4">
          <p className="text-sm leading-6 text-slate-600">
            Delete <span className="font-semibold text-slate-900">{deleteCandidate?.title}</span>?
            This action cannot be undone.
          </p>
          <div className="flex flex-col-reverse gap-2 sm:flex-row sm:justify-end">
            <Button onClick={() => setDeleteCandidate(null)}>Cancel</Button>
            <Button
              disabled={Boolean(
                deleteCandidate && actionKey === `delete:${deleteCandidate.id}`,
              )}
              onClick={() => {
                const task = deleteCandidate;
                setDeleteCandidate(null);
                runAction(
                  `delete:${task.id}`,
                  () => deleteTask(task.id),
                  "Task deleted.",
                );
              }}
              variant="danger"
            >
              {deleteCandidate && actionKey === `delete:${deleteCandidate.id}`
                ? "Deleting..."
                : "Delete task"}
            </Button>
          </div>
        </div>
      </Modal>
    </section>
  );
}

export default ClassTasksPage;
