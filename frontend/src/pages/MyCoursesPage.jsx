import { useCallback, useEffect, useMemo, useState } from "react";
import { Link, useParams } from "react-router-dom";

import { listMyClassrooms } from "../api/classrooms.js";
import {
  dropClassCourse,
  listClassCourses,
  listMyCourses,
  registerClassCourse,
} from "../api/courses.js";
import Alert from "../components/Alert.jsx";
import ClassWorkspaceHeader from "../components/ClassWorkspaceHeader.jsx";
import LoadingScreen from "../components/LoadingScreen.jsx";
import StatusBadge from "../components/StatusBadge.jsx";
import { isApproved } from "../utils/classrooms.js";
import { formatCourseTitle } from "../utils/courses.js";
import { parseApiError } from "../utils/errors.js";

function CourseSummary({ classCourse }) {
  return (
    <div>
      <h3 className="text-base font-semibold text-slate-950">
        {classCourse.course.name}
      </h3>
      <p className="mt-1 text-sm font-medium text-blue-600">
        {classCourse.course.code}
      </p>
      <div className="mt-3 flex flex-wrap gap-2">
        <StatusBadge value={classCourse.is_default ? "default" : "optional"} />
        <StatusBadge value={classCourse.is_active ? "active" : "inactive"} />
      </div>
      <p className="mt-3 text-sm text-slate-500">
        Instructor: {classCourse.instructor_name || "Not set"}
      </p>
    </div>
  );
}

function MyCoursesPage() {
  const { classId } = useParams();
  const numericClassId = Number(classId);
  const [classroom, setClassroom] = useState(null);
  const [membership, setMembership] = useState(null);
  const [classCourses, setClassCourses] = useState([]);
  const [registrations, setRegistrations] = useState([]);
  const [isLoading, setIsLoading] = useState(true);
  const [actionKey, setActionKey] = useState("");
  const [confirmDropId, setConfirmDropId] = useState(null);
  const [error, setError] = useState(null);
  const [actionError, setActionError] = useState(null);
  const [success, setSuccess] = useState("");

  const registrationByClassCourse = useMemo(() => {
    return new Map(
      registrations.map((registration) => [
        registration.class_course_id,
        registration,
      ]),
    );
  }, [registrations]);

  const activeClassCourses = useMemo(
    () => classCourses.filter((classCourse) => classCourse.is_active),
    [classCourses],
  );

  const activeRegistrationCount = useMemo(
    () => registrations.length,
    [registrations],
  );

  const loadCourses = useCallback(async () => {
    setError(null);
    setActionError(null);

    try {
      const myClassrooms = await listMyClassrooms();
      const mineRecord = myClassrooms.find(
        (item) => item.id === numericClassId,
      );

      if (!mineRecord) {
        setClassroom(null);
        setMembership(null);
        setClassCourses([]);
        setRegistrations([]);
        setError({
          message: "This class is not in your memberships.",
          items: [],
        });
        return;
      }

      setClassroom(mineRecord);
      setMembership(mineRecord.membership);

      if (!isApproved(mineRecord.membership)) {
        setClassCourses([]);
        setRegistrations([]);
        return;
      }

      const [classCourseData, registrationData] = await Promise.all([
        listClassCourses(numericClassId),
        listMyCourses(numericClassId),
      ]);
      setClassCourses(classCourseData);
      setRegistrations(registrationData);
    } catch (apiError) {
      setError(parseApiError(apiError));
    }
  }, [numericClassId]);

  useEffect(() => {
    let isMounted = true;

    async function load() {
      await loadCourses();
      if (isMounted) {
        setIsLoading(false);
      }
    }

    load();

    return () => {
      isMounted = false;
    };
  }, [loadCourses]);

  async function handleRegister(classCourse) {
    setActionKey(`register:${classCourse.id}`);
    setActionError(null);
    setSuccess("");

    try {
      await registerClassCourse(classCourse.id);
      setSuccess(`${formatCourseTitle(classCourse.course)} was registered.`);
      await loadCourses();
    } catch (apiError) {
      setActionError(parseApiError(apiError));
    } finally {
      setActionKey("");
    }
  }

  async function handleDrop(classCourse) {
    setActionKey(`drop:${classCourse.id}`);
    setActionError(null);
    setSuccess("");

    try {
      await dropClassCourse(classCourse.id);
      setConfirmDropId(null);
      setSuccess(`${formatCourseTitle(classCourse.course)} was dropped.`);
      await loadCourses();
    } catch (apiError) {
      setActionError(parseApiError(apiError));
    } finally {
      setActionKey("");
    }
  }

  if (isLoading) {
    return <LoadingScreen message="Loading your courses..." />;
  }

  if (error && !classroom) {
    return (
      <section className="space-y-5">
        <Alert
          title="Could not load courses"
          message={error.message}
          items={error.items}
        />
        <Link
          to="/classes"
          className="inline-flex rounded-md bg-blue-600 px-4 py-2.5 text-sm font-semibold text-white transition hover:bg-blue-700 focus:outline-none focus:ring-2 focus:ring-blue-600 focus:ring-offset-2"
        >
          Back to classes
        </Link>
      </section>
    );
  }

  return (
    <section className="space-y-6">
      <ClassWorkspaceHeader classroom={classroom} membership={membership} />

      {error ? (
        <Alert title="Course access blocked" message={error.message} items={error.items} />
      ) : null}

      {!isApproved(membership) ? (
        <div className="rounded-md border border-amber-200 bg-amber-50 p-5">
          <h2 className="text-lg font-semibold text-slate-950">
            Membership {membership?.status}
          </h2>
          <p className="mt-2 text-sm leading-6 text-amber-700">
            Your course registrations are available after a representative
            approves your class membership.
          </p>
        </div>
      ) : (
        <>
          {actionError ? (
            <Alert
              title="Course action failed"
              message={actionError.message}
              items={actionError.items}
            />
          ) : null}
          {success ? (
            <Alert type="success" title="Updated" message={success} />
          ) : null}

          <div className="rounded-md border border-slate-200 bg-white p-5 shadow-sm sm:p-6">
            <div className="flex items-center justify-between">
              <div>
                <h2 className="text-lg font-semibold text-slate-950">
                  Active Registrations
                </h2>
                <p className="mt-1 text-sm text-slate-500">
                  Courses you are currently registered in, including courses
                  that were added as defaults.
                </p>
              </div>
              <span className="text-sm font-medium text-slate-500">
                {activeRegistrationCount} active
              </span>
            </div>

            {registrations.length === 0 ? (
              <p className="mt-5 rounded-md border border-dashed border-slate-200 p-4 text-sm text-slate-500">
                No active course registrations.
              </p>
            ) : (
              <div className="mt-5 grid gap-4 md:grid-cols-2">
                {registrations.map((registration) => {
                  const classCourse = registration.class_course;
                  const isBusy = actionKey?.endsWith(`:${classCourse.id}`);

                  return (
                  <div
                    key={registration.id}
                    className="grid gap-4 rounded-md border border-slate-200 bg-slate-50 p-4 lg:grid-cols-[1fr_auto] lg:items-center"
                  >
                    <div>
                      <CourseSummary classCourse={classCourse} />
                      <p className="mt-3 text-xs font-medium text-slate-500">
                        Registered {new Date(registration.registered_at).toLocaleString()}
                      </p>
                    </div>
                    <div className="flex flex-wrap gap-2 lg:justify-end">
                      {confirmDropId === classCourse.id ? (
                        <div className="flex flex-wrap items-center gap-2 rounded-md border border-red-200 bg-red-50 p-2">
                          <span className="text-sm font-medium text-red-700">
                            Drop?
                          </span>
                          <button
                            type="button"
                            disabled={isBusy}
                            onClick={() => handleDrop(classCourse)}
                            className="rounded-md bg-red-600 px-3 py-1.5 text-sm font-semibold text-white transition hover:bg-red-700 focus:outline-none focus:ring-2 focus:ring-red-600 focus:ring-offset-2 disabled:cursor-not-allowed disabled:opacity-60"
                          >
                            {actionKey === `drop:${classCourse.id}`
                              ? "Dropping..."
                              : "Yes"}
                          </button>
                          <button
                            type="button"
                            disabled={isBusy}
                            onClick={() => setConfirmDropId(null)}
                            className="rounded-md border border-slate-200 px-3 py-1.5 text-sm font-semibold text-slate-600 transition hover:bg-white focus:outline-none focus:ring-2 focus:ring-blue-600 focus:ring-offset-2"
                          >
                            Cancel
                          </button>
                        </div>
                      ) : (
                        <button
                          type="button"
                          onClick={() => setConfirmDropId(classCourse.id)}
                          className="rounded-md border border-red-200 px-4 py-2 text-sm font-semibold text-red-700 transition hover:bg-red-50 focus:outline-none focus:ring-2 focus:ring-red-600 focus:ring-offset-2"
                        >
                          Drop
                        </button>
                      )}
                    </div>
                  </div>
                  );
                })}
              </div>
            )}
          </div>

          <div className="rounded-md border border-slate-200 bg-white p-5 shadow-sm sm:p-6">
            <div className="flex items-center justify-between">
              <div>
                <h2 className="text-lg font-semibold text-slate-950">
                  Available Class Courses
                </h2>
                <p className="mt-1 text-sm text-slate-500">
                  Register or re-register any active course in this class.
                </p>
              </div>
              <span className="text-sm font-medium text-slate-500">
                {activeClassCourses.length} active
              </span>
            </div>

            {activeClassCourses.length === 0 ? (
              <p className="mt-5 rounded-md border border-dashed border-slate-200 p-4 text-sm text-slate-500">
                No active class courses are available.
              </p>
            ) : (
              <div className="mt-5 space-y-4">
                {activeClassCourses.map((classCourse) => {
                  const registration = registrationByClassCourse.get(
                    classCourse.id,
                  );
                  const isRegistered = Boolean(registration);
                  const isBusy = actionKey?.endsWith(`:${classCourse.id}`);

                  return (
                    <div
                      key={classCourse.id}
                      className="grid gap-4 rounded-md border border-slate-200 p-4 lg:grid-cols-[1fr_auto] lg:items-center"
                    >
                      <CourseSummary classCourse={classCourse} />
                      <div className="flex flex-wrap gap-2 lg:justify-end">
                        {isRegistered ? (
                          <span className="rounded-md border border-emerald-200 bg-blue-50 px-4 py-2 text-sm font-semibold text-emerald-700">
                            Registered
                          </span>
                        ) : (
                          <button
                            type="button"
                            disabled={isBusy}
                            onClick={() => handleRegister(classCourse)}
                            className="rounded-md bg-blue-600 px-4 py-2 text-sm font-semibold text-white transition hover:bg-blue-700 focus:outline-none focus:ring-2 focus:ring-blue-600 focus:ring-offset-2 disabled:cursor-not-allowed disabled:bg-blue-300"
                          >
                            {actionKey === `register:${classCourse.id}`
                              ? "Registering..."
                              : "Register"}
                          </button>
                        )}
                      </div>
                    </div>
                  );
                })}
              </div>
            )}
          </div>
        </>
      )}
    </section>
  );
}

export default MyCoursesPage;

