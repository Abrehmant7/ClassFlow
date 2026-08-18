import { useEffect, useState } from "react";
import { Link } from "react-router-dom";

import { listMyClassrooms } from "../api/classrooms.js";
import Alert from "../components/Alert.jsx";
import Button from "../components/Button.jsx";
import EmptyState from "../components/EmptyState.jsx";
import LoadingScreen from "../components/LoadingScreen.jsx";
import PageHeader from "../components/PageHeader.jsx";
import StatusBadge from "../components/StatusBadge.jsx";
import { formatClassTitle } from "../utils/classrooms.js";
import { parseApiError } from "../utils/errors.js";

function ClassCard({ classroom }) {
  const pending = classroom.membership.status !== "approved";

  return (
    <Link
      className={`group block rounded-lg border bg-white p-4 shadow-sm transition hover:-translate-y-0.5 hover:border-blue-200 hover:shadow-md cf-focus ${
        pending ? "border-amber-200" : "border-slate-200"
      }`}
      to={`/classes/${classroom.id}`}
    >
      <div className="flex items-start justify-between gap-4">
        <div className="min-w-0">
          <h2 className="truncate text-base font-semibold text-slate-900">
            {classroom.name}
          </h2>
          <p className="mt-1 text-sm text-slate-500">
            Semester {classroom.semester} / Section {classroom.section}
          </p>
        </div>
        <span
          aria-hidden="true"
          className="text-lg text-slate-300 transition group-hover:text-blue-600"
        >
          {"->"}
        </span>
      </div>

      <div className="mt-4 flex flex-wrap items-center gap-2">
        <StatusBadge value={classroom.membership.role} subtle />
        {pending ? (
          <StatusBadge value={classroom.membership.status} />
        ) : (
          <span className="text-xs font-medium text-emerald-700">Approved</span>
        )}
      </div>

      {pending ? (
        <p className="mt-3 text-sm leading-6 text-amber-700">
          Waiting for a representative to approve your request.
        </p>
      ) : classroom.description ? (
        <p className="mt-3 line-clamp-2 text-sm leading-6 text-slate-500">
          {classroom.description}
        </p>
      ) : (
        <p className="mt-3 text-sm leading-6 text-slate-500">
          {formatClassTitle(classroom)}
        </p>
      )}
    </Link>
  );
}

function MyClassesPage() {
  const [classrooms, setClassrooms] = useState([]);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState(null);

  useEffect(() => {
    let isMounted = true;

    async function loadClassrooms() {
      try {
        const data = await listMyClassrooms();
        if (isMounted) {
          setClassrooms(data);
        }
      } catch (apiError) {
        if (isMounted) {
          setError(parseApiError(apiError));
        }
      } finally {
        if (isMounted) {
          setIsLoading(false);
        }
      }
    }

    loadClassrooms();

    return () => {
      isMounted = false;
    };
  }, []);

  if (isLoading) {
    return <LoadingScreen message="Loading your classes..." />;
  }

  return (
    <section className="space-y-6">
      <PageHeader
        actions={
          <>
            <Link to="/classes/join">
              <Button>Join class</Button>
            </Link>
            <Link to="/classes/new">
              <Button variant="primary">Create class</Button>
            </Link>
          </>
        }
        eyebrow="Classes"
        title="My Classes"
      />

      {error ? (
        <Alert
          title="Could not load classes"
          message={error.message}
          items={error.items}
        />
      ) : null}

      {classrooms.length === 0 ? (
        <EmptyState
          action={
            <div className="flex flex-wrap justify-center gap-2">
              <Link to="/classes/join">
                <Button>Join class</Button>
              </Link>
              <Link to="/classes/new">
                <Button variant="primary">Create class</Button>
              </Link>
            </div>
          }
          message="Create a class as a representative or request access with a class ID and join code."
          title="No classes yet"
        />
      ) : (
        <div className="grid gap-4 md:grid-cols-2 xl:grid-cols-3">
          {classrooms.map((classroom) => (
            <ClassCard classroom={classroom} key={classroom.id} />
          ))}
        </div>
      )}
    </section>
  );
}

export default MyClassesPage;
