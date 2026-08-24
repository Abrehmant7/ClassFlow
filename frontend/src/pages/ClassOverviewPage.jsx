import { useCallback, useEffect, useMemo, useState } from "react";
import { Link, useParams } from "react-router-dom";

import { listMyClassrooms } from "../api/classrooms.js";
import { listClassCourses, listMyCourses } from "../api/courses.js";
import { createTask, listTasks, updateTaskProgress } from "../api/tasks.js";
import Alert from "../components/Alert.jsx";
import Button from "../components/Button.jsx";
import ClassWorkspaceHeader from "../components/ClassWorkspaceHeader.jsx";
import EmptyState from "../components/EmptyState.jsx";
import LoadingScreen from "../components/LoadingScreen.jsx";
import SharedTaskModal from "../components/SharedTaskModal.jsx";
import StatusBadge from "../components/StatusBadge.jsx";
import TaskProgressButton from "../components/TaskProgressButton.jsx";
import TaskRow from "../components/TaskRow.jsx";
import { isApproved, isRepresentative } from "../utils/classrooms.js";
import { parseApiError } from "../utils/errors.js";

function isCompletedTask(task) {
  return task.my_progress?.status === "completed";
}

function ClassOverviewPage() {
  const { classId } = useParams();
  const numericClassId = Number(classId);
  const [classroom, setClassroom] = useState(null);
  const [membership, setMembership] = useState(null);
  const [tasks, setTasks] = useState([]);
  const [courses, setCourses] = useState([]);
  const [registrations, setRegistrations] = useState([]);
  const [isCreateOpen, setIsCreateOpen] = useState(false);
  const [isLoading, setIsLoading] = useState(true);
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [actionKey, setActionKey] = useState("");
  const [error, setError] = useState(null);
  const [actionError, setActionError] = useState(null);
  const [success, setSuccess] = useState("");

  const canManage = useMemo(() => isRepresentative(membership), [membership]);
  const activeClassCourses = useMemo(
    () => courses.filter((course) => course.is_active),
    [courses],
  );

  const loadOverview = useCallback(async () => {
    setError(null);

    try {
      const myClassrooms = await listMyClassrooms();
      const mineRecord = myClassrooms.find((item) => item.id === numericClassId);

      if (!mineRecord) {
        setClassroom(null);
        setMembership(null);
        setError({ message: "This class is not in your memberships.", items: [] });
        return;
      }

      setClassroom(mineRecord);
      setMembership(mineRecord.membership);

      if (!isApproved(mineRecord.membership)) {
        return;
      }

      const [taskData, courseData, registrationData] = await Promise.all([
        listTasks(numericClassId, false),
        listClassCourses(numericClassId, isRepresentative(mineRecord.membership)),
        listMyCourses(numericClassId),
      ]);
      setTasks(taskData.filter((task) => !isCompletedTask(task)).slice(0, 5));
      setCourses(courseData);
      setRegistrations(registrationData);
    } catch (apiError) {
      setError(parseApiError(apiError));
    }
  }, [numericClassId]);

  async function runAction(key, action, message) {
    setActionKey(key);
    setActionError(null);
    setSuccess("");

    try {
      await action();
      setSuccess(message);
      await loadOverview();
    } catch (apiError) {
      setActionError(parseApiError(apiError));
    } finally {
      setActionKey("");
    }
  }

  async function handleCreateSharedTask(payload) {
    setIsSubmitting(true);
    setActionError(null);
    setSuccess("");

    try {
      const created = await createTask(numericClassId, payload);
      setSuccess(`${created.title} was created.`);
      await loadOverview();
      return created;
    } catch (apiError) {
      setActionError(parseApiError(apiError));
      return null;
    } finally {
      setIsSubmitting(false);
    }
  }

  useEffect(() => {
    let isMounted = true;

    async function load() {
      await loadOverview();
      if (isMounted) {
        setIsLoading(false);
      }
    }

    load();

    return () => {
      isMounted = false;
    };
  }, [loadOverview]);

  if (isLoading) {
    return <LoadingScreen message="Loading class overview..." />;
  }

  if (error && !classroom) {
    return (
      <section className="space-y-5">
        <Alert title="Could not load class" message={error.message} items={error.items} />
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
          canManage ? (
            <Button onClick={() => setIsCreateOpen(true)} variant="primary">
              Create shared task
            </Button>
          ) : null
        }
        classroom={classroom}
        membership={membership}
      />

      {error ? (
        <Alert title="Class access blocked" message={error.message} items={error.items} />
      ) : null}
      {actionError ? (
        <Alert
          title="Task action failed"
          message={actionError.message}
          items={actionError.items}
        />
      ) : null}
      {success ? <Alert type="success" title="Updated" message={success} /> : null}

      {!isApproved(membership) ? (
        <Alert
          items={[]}
          message="Protected class content is available after a representative approves your membership."
          title={`Membership ${membership?.status}`}
          type="warning"
        />
      ) : (
        <div className="grid gap-4 lg:grid-cols-[1.35fr_0.65fr]">
          <div className="cf-card p-5">
            <div className="flex items-center justify-between">
              <h2 className="text-base font-semibold text-slate-900">
                Upcoming tasks
              </h2>
              <Link
                className="text-sm font-semibold text-blue-700 hover:text-blue-900 cf-focus"
                to={`/classes/${numericClassId}/tasks`}
              >
                View all
              </Link>
            </div>
            {tasks.length === 0 ? (
              <div className="mt-4">
                <EmptyState
                  message="There are no pending tasks in this class."
                  title="All clear"
                />
              </div>
            ) : (
              <div className="mt-4 space-y-2">
                {tasks.map((task) => {
                  const isBusy = actionKey === `progress:${task.id}`;

                  return (
                    <TaskRow
                      key={task.id}
                      progressControl={
                        <TaskProgressButton
                          checked={false}
                          disabled={task.status !== "active"}
                          isBusy={isBusy}
                          onClick={() =>
                            runAction(
                              `progress:${task.id}`,
                              () => updateTaskProgress(task.id, "completed"),
                              "Task marked complete.",
                            )
                          }
                        />
                      }
                      task={task}
                    />
                  );
                })}
              </div>
            )}
          </div>

          <div className="space-y-4">
            <div className="cf-card p-5">
              <h2 className="text-base font-semibold text-slate-900">
                Courses
              </h2>
              <div className="mt-4 grid grid-cols-2 gap-3">
                <div>
                  <p className="text-2xl font-bold text-slate-900">
                    {registrations.length}
                  </p>
                  <p className="text-xs font-medium text-slate-500">
                    Registered
                  </p>
                </div>
                <div>
                  <p className="text-2xl font-bold text-slate-900">
                    {courses.filter((course) => course.is_active).length}
                  </p>
                  <p className="text-xs font-medium text-slate-500">
                    Active
                  </p>
                </div>
              </div>
              <Link
                className="mt-4 inline-flex text-sm font-semibold text-blue-700 hover:text-blue-900 cf-focus"
                to={`/classes/${numericClassId}/courses`}
              >
                Manage courses
              </Link>
            </div>

            <div className="cf-card p-5">
              <h2 className="text-base font-semibold text-slate-900">
                Membership
              </h2>
              <div className="mt-3 flex flex-wrap gap-2">
                <StatusBadge value={membership?.role} />
                <StatusBadge value={membership?.status} />
              </div>
              {canManage && classroom?.join_code ? (
                <p className="mt-3 text-sm text-slate-500">
                  Join code: <span className="font-semibold text-slate-900">{classroom.join_code}</span>
                </p>
              ) : null}
            </div>
          </div>
        </div>
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
    </section>
  );
}

export default ClassOverviewPage;
