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
import LoadingScreen from "../components/LoadingScreen.jsx";
import StatusBadge from "../components/StatusBadge.jsx";
import { isApproved } from "../utils/classrooms.js";
import { formatCourseTitle } from "../utils/courses.js";
import { parseApiError } from "../utils/errors.js";

function CourseSummary({ classCourse }) {
  return (
    <div>
      <h3 className="text-base font-semibold text-[#172033]">
        {classCourse.course.name}
      </h3>
      <p className="mt-1 text-sm font-medium text-[#256f68]">
        {classCourse.course.code}
      </p>
      <div className="mt-3 flex flex-wrap gap-2">
        <StatusBadge value={classCourse.is_default ? "default" : "optional"} />
        <StatusBadge value={classCourse.is_active ? "active" : "inactive"} />
      </div>
      <p className="mt-3 text-sm text-[#566176]">
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
          className="inline-flex rounded-md bg-[#256f68] px-4 py-2.5 text-sm font-semibold text-white transition hover:bg-[#1f5d58] focus:outline-none focus:ring-2 focus:ring-[#256f68] focus:ring-offset-2"
        >
          Back to classes
        </Link>
      </section>
    );
  }

  return (
    <section className="space-y-6">
      <div className="flex flex-col gap-4 lg:flex-row lg:items-end lg:justify-between">
        <div>
          <p className="text-sm font-semibold uppercase tracking-wide text-[#256f68]">
            My courses
          </p>
          <h1 className="mt-2 text-3xl font-bold text-[#172033]">
            {classroom?.name}
          </h1>
          <p className="mt-3 max-w-2xl text-base leading-7 text-[#566176]">
            Active registrations for this class, including automatically
            registered default courses.
          </p>
        </div>
        <div className="flex flex-wrap gap-2">
          <Link
            to={`/classes/${numericClassId}`}
            className="rounded-md border border-[#cbd5e1] px-4 py-2 text-sm font-semibold text-[#344056] transition hover:bg-white focus:outline-none focus:ring-2 focus:ring-[#256f68] focus:ring-offset-2"
          >
            Class details
          </Link>
          <Link
            to={`/classes/${numericClassId}/courses`}
            className="rounded-md border border-[#cbd5e1] px-4 py-2 text-sm font-semibold text-[#344056] transition hover:bg-white focus:outline-none focus:ring-2 focus:ring-[#256f68] focus:ring-offset-2"
          >
            Class courses
          </Link>
        </div>
      </div>

      {error ? (
        <Alert title="Course access blocked" message={error.message} items={error.items} />
      ) : null}

      {!isApproved(membership) ? (
        <div className="rounded-md border border-[#f2cf82] bg-[#fffaf0] p-5">
          <h2 className="text-lg font-semibold text-[#172033]">
            Membership {membership?.status}
          </h2>
          <p className="mt-2 text-sm leading-6 text-[#7a4b00]">
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

          <div className="rounded-md border border-[#dde4ef] bg-white p-5 shadow-sm sm:p-6">
            <div className="flex items-center justify-between">
              <div>
                <h2 className="text-lg font-semibold text-[#172033]">
                  Active Registrations
                </h2>
                <p className="mt-1 text-sm text-[#566176]">
                  Courses you are currently registered in, including courses
                  that were added as defaults.
                </p>
              </div>
              <span className="text-sm font-medium text-[#566176]">
                {activeRegistrationCount} active
              </span>
            </div>

            {registrations.length === 0 ? (
              <p className="mt-5 rounded-md border border-dashed border-[#cbd5e1] p-4 text-sm text-[#566176]">
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
                    className="grid gap-4 rounded-md border border-[#dde4ef] bg-[#f8fafc] p-4 lg:grid-cols-[1fr_auto] lg:items-center"
                  >
                    <div>
                      <CourseSummary classCourse={classCourse} />
                      <p className="mt-3 text-xs font-medium text-[#667085]">
                        Registered {new Date(registration.registered_at).toLocaleString()}
                      </p>
                    </div>
                    <div className="flex flex-wrap gap-2 lg:justify-end">
                      {confirmDropId === classCourse.id ? (
                        <div className="flex flex-wrap items-center gap-2 rounded-md border border-[#f5b5b5] bg-[#fff8f8] p-2">
                          <span className="text-sm font-medium text-[#7f1d1d]">
                            Drop?
                          </span>
                          <button
                            type="button"
                            disabled={isBusy}
                            onClick={() => handleDrop(classCourse)}
                            className="rounded-md bg-[#b42318] px-3 py-1.5 text-sm font-semibold text-white transition hover:bg-[#971c14] focus:outline-none focus:ring-2 focus:ring-[#b42318] focus:ring-offset-2 disabled:cursor-not-allowed disabled:opacity-60"
                          >
                            {actionKey === `drop:${classCourse.id}`
                              ? "Dropping..."
                              : "Yes"}
                          </button>
                          <button
                            type="button"
                            disabled={isBusy}
                            onClick={() => setConfirmDropId(null)}
                            className="rounded-md border border-[#cbd5e1] px-3 py-1.5 text-sm font-semibold text-[#344056] transition hover:bg-white focus:outline-none focus:ring-2 focus:ring-[#256f68] focus:ring-offset-2"
                          >
                            Cancel
                          </button>
                        </div>
                      ) : (
                        <button
                          type="button"
                          onClick={() => setConfirmDropId(classCourse.id)}
                          className="rounded-md border border-[#f5b5b5] px-4 py-2 text-sm font-semibold text-[#7f1d1d] transition hover:bg-[#fff1f1] focus:outline-none focus:ring-2 focus:ring-[#b42318] focus:ring-offset-2"
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

          <div className="rounded-md border border-[#dde4ef] bg-white p-5 shadow-sm sm:p-6">
            <div className="flex items-center justify-between">
              <div>
                <h2 className="text-lg font-semibold text-[#172033]">
                  Available Class Courses
                </h2>
                <p className="mt-1 text-sm text-[#566176]">
                  Register or re-register any active course in this class.
                </p>
              </div>
              <span className="text-sm font-medium text-[#566176]">
                {activeClassCourses.length} active
              </span>
            </div>

            {activeClassCourses.length === 0 ? (
              <p className="mt-5 rounded-md border border-dashed border-[#cbd5e1] p-4 text-sm text-[#566176]">
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
                      className="grid gap-4 rounded-md border border-[#dde4ef] p-4 lg:grid-cols-[1fr_auto] lg:items-center"
                    >
                      <CourseSummary classCourse={classCourse} />
                      <div className="flex flex-wrap gap-2 lg:justify-end">
                        {isRegistered ? (
                          <span className="rounded-md border border-[#9ed8cb] bg-[#ecfdf7] px-4 py-2 text-sm font-semibold text-[#14534a]">
                            Registered
                          </span>
                        ) : (
                          <button
                            type="button"
                            disabled={isBusy}
                            onClick={() => handleRegister(classCourse)}
                            className="rounded-md bg-[#256f68] px-4 py-2 text-sm font-semibold text-white transition hover:bg-[#1f5d58] focus:outline-none focus:ring-2 focus:ring-[#256f68] focus:ring-offset-2 disabled:cursor-not-allowed disabled:bg-[#8ebbb5]"
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
