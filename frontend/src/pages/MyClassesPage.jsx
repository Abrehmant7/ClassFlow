import { useEffect, useState } from "react";
import { Link } from "react-router-dom";

import { listMyClassrooms } from "../api/classrooms.js";
import Alert from "../components/Alert.jsx";
import LoadingScreen from "../components/LoadingScreen.jsx";
import StatusBadge from "../components/StatusBadge.jsx";
import { formatClassTitle } from "../utils/classrooms.js";
import { parseApiError } from "../utils/errors.js";

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
      <div className="flex flex-col gap-4 sm:flex-row sm:items-end sm:justify-between">
        <div>
          <p className="text-sm font-semibold uppercase tracking-wide text-[#256f68]">
            Classes
          </p>
          <h1 className="mt-2 text-3xl font-bold text-[#172033]">
            My Classes
          </h1>
          <p className="mt-3 max-w-2xl text-base leading-7 text-[#566176]">
            Classes you created or joined appear here with your current
            membership status.
          </p>
        </div>

        <div className="flex flex-col gap-2 sm:flex-row">
          <Link
            to="/classes/join"
            className="inline-flex items-center justify-center rounded-md border border-[#cbd5e1] px-4 py-2.5 text-sm font-semibold text-[#344056] transition hover:border-[#8ea0b8] hover:bg-white focus:outline-none focus:ring-2 focus:ring-[#256f68] focus:ring-offset-2"
          >
            Join class
          </Link>
          <Link
            to="/classes/new"
            className="inline-flex items-center justify-center rounded-md bg-[#256f68] px-4 py-2.5 text-sm font-semibold text-white transition hover:bg-[#1f5d58] focus:outline-none focus:ring-2 focus:ring-[#256f68] focus:ring-offset-2"
          >
            Create class
          </Link>
        </div>
      </div>

      {error ? (
        <Alert
          title="Could not load classes"
          message={error.message}
          items={error.items}
        />
      ) : null}

      {classrooms.length === 0 ? (
        <div className="rounded-md border border-dashed border-[#cbd5e1] bg-white p-8 text-center">
          <h2 className="text-lg font-semibold text-[#172033]">
            No classes yet
          </h2>
          <p className="mx-auto mt-2 max-w-xl text-sm leading-6 text-[#566176]">
            Create a class as a representative or request access with a class ID
            and join code.
          </p>
        </div>
      ) : (
        <div className="grid gap-4 md:grid-cols-2">
          {classrooms.map((classroom) => (
            <Link
              key={classroom.id}
              to={`/classes/${classroom.id}`}
              className="rounded-md border border-[#dde4ef] bg-white p-5 shadow-sm transition hover:border-[#aac7c2] hover:shadow-md focus:outline-none focus:ring-2 focus:ring-[#256f68] focus:ring-offset-2"
            >
              <div className="flex flex-col gap-3 sm:flex-row sm:items-start sm:justify-between">
                <div>
                  <h2 className="text-lg font-semibold text-[#172033]">
                    {classroom.name}
                  </h2>
                  <p className="mt-1 text-sm text-[#566176]">
                    Semester {classroom.semester} · Section {classroom.section}
                  </p>
                </div>
                <div className="flex flex-wrap gap-2">
                  <StatusBadge value={classroom.membership.role} />
                  <StatusBadge value={classroom.membership.status} />
                </div>
              </div>
              <p className="mt-4 line-clamp-2 text-sm leading-6 text-[#566176]">
                {classroom.description || formatClassTitle(classroom)}
              </p>
            </Link>
          ))}
        </div>
      )}
    </section>
  );
}

export default MyClassesPage;
