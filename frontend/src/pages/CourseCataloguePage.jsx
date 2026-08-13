import { useEffect, useMemo, useState } from "react";

import { createCourse, listCourses } from "../api/courses.js";
import { listMyClassrooms } from "../api/classrooms.js";
import Alert from "../components/Alert.jsx";
import FormField from "../components/FormField.jsx";
import LoadingScreen from "../components/LoadingScreen.jsx";
import TextAreaField from "../components/TextAreaField.jsx";
import { isRepresentative } from "../utils/classrooms.js";
import {
  formatCourseTitle,
  normalizeCourseCode,
  normalizeCourseName,
} from "../utils/courses.js";
import { parseApiError } from "../utils/errors.js";

const initialCreateForm = {
  name: "",
  code: "",
  description: "",
};

function CourseCard({ course }) {
  return (
    <div className="rounded-md border border-[#dde4ef] bg-white p-4 shadow-sm">
      <div className="flex flex-col gap-2 sm:flex-row sm:items-start sm:justify-between">
        <div>
          <h2 className="text-base font-semibold text-[#172033]">
            {course.name}
          </h2>
          <p className="mt-1 text-sm font-medium text-[#256f68]">
            {course.code}
          </p>
        </div>
        <span className="text-xs font-medium text-[#667085]">
          Course #{course.id}
        </span>
      </div>
      {course.description ? (
        <p className="mt-3 text-sm leading-6 text-[#566176]">
          {course.description}
        </p>
      ) : null}
    </div>
  );
}

function CourseCataloguePage() {
  const [search, setSearch] = useState("");
  const [courses, setCourses] = useState([]);
  const [matchingCourses, setMatchingCourses] = useState([]);
  const [representativeReady, setRepresentativeReady] = useState(false);
  const [isLoading, setIsLoading] = useState(true);
  const [isSearching, setIsSearching] = useState(false);
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [error, setError] = useState(null);
  const [createError, setCreateError] = useState(null);
  const [success, setSuccess] = useState("");
  const [form, setForm] = useState(initialCreateForm);

  const hasExactMatch = useMemo(() => {
    const normalizedName = normalizeCourseName(form.name).toLowerCase();
    const normalizedCode = normalizeCourseCode(form.code).toLowerCase();

    return courses.some(
      (course) =>
        course.name.toLowerCase() === normalizedName ||
        course.code.toLowerCase() === normalizedCode,
    );
  }, [courses, form.code, form.name]);

  useEffect(() => {
    let isMounted = true;

    async function loadInitialData() {
      try {
        const [courseData, classrooms] = await Promise.all([
          listCourses(),
          listMyClassrooms(),
        ]);

        if (!isMounted) return;
        setCourses(courseData);
        setRepresentativeReady(
          classrooms.some((classroom) => isRepresentative(classroom.membership)),
        );
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

    loadInitialData();

    return () => {
      isMounted = false;
    };
  }, []);

  async function handleSearch(event) {
    event.preventDefault();
    setIsSearching(true);
    setError(null);
    setSuccess("");

    try {
      const data = await listCourses(search.trim());
      setCourses(data);
    } catch (apiError) {
      setError(parseApiError(apiError));
    } finally {
      setIsSearching(false);
    }
  }

  function handleChange(event) {
    const { name, value } = event.target;
    setForm((current) => ({ ...current, [name]: value }));
  }

  async function handleCreate(event) {
    event.preventDefault();
    setIsSubmitting(true);
    setCreateError(null);
    setMatchingCourses([]);
    setSuccess("");

    try {
      const payload = {
        name: normalizeCourseName(form.name),
        code: normalizeCourseCode(form.code),
      };

      const description = form.description.trim();
      if (description) {
        payload.description = description;
      }

      const created = await createCourse(payload);
      setCourses((current) => [created, ...current]);
      setSuccess(`${formatCourseTitle(created)} was added to the catalogue.`);
      setForm(initialCreateForm);
    } catch (apiError) {
      const parsed = parseApiError(apiError);
      setCreateError(parsed);

      if (apiError.response?.status === 409) {
        const [codeMatches, nameMatches] = await Promise.all([
          form.code.trim() ? listCourses(form.code.trim()) : Promise.resolve([]),
          form.name.trim() ? listCourses(form.name.trim()) : Promise.resolve([]),
        ]);
        const uniqueMatches = [...codeMatches, ...nameMatches].filter(
          (course, index, all) =>
            all.findIndex((item) => item.id === course.id) === index,
        );
        setMatchingCourses(uniqueMatches);
      }
    } finally {
      setIsSubmitting(false);
    }
  }

  if (isLoading) {
    return <LoadingScreen message="Loading course catalogue..." />;
  }

  return (
    <section className="space-y-6">
      <div>
        <p className="text-sm font-semibold uppercase tracking-wide text-[#256f68]">
          Catalogue
        </p>
        <h1 className="mt-2 text-3xl font-bold text-[#172033]">
          Global Course Catalogue
        </h1>
        <p className="mt-3 max-w-2xl text-base leading-7 text-[#566176]">
          Search reusable courses by name or code before creating a missing
          catalogue entry.
        </p>
      </div>

      {error ? (
        <Alert
          title="Could not load courses"
          message={error.message}
          items={error.items}
        />
      ) : null}

      <form
        className="rounded-md border border-[#dde4ef] bg-white p-5 shadow-sm"
        onSubmit={handleSearch}
      >
        <div className="flex flex-col gap-3 sm:flex-row">
          <div className="flex-1">
            <FormField
              id="catalogue-search"
              label="Search catalogue"
              name="search"
              onChange={(event) => setSearch(event.target.value)}
              placeholder="Database Systems or CS101"
              value={search}
            />
          </div>
          <button
            type="submit"
            disabled={isSearching}
            className="mt-6 inline-flex items-center justify-center rounded-md bg-[#256f68] px-5 py-2.5 text-sm font-semibold text-white transition hover:bg-[#1f5d58] focus:outline-none focus:ring-2 focus:ring-[#256f68] focus:ring-offset-2 disabled:cursor-not-allowed disabled:bg-[#8ebbb5] sm:self-start"
          >
            {isSearching ? "Searching..." : "Search"}
          </button>
        </div>
      </form>

      <div className="grid gap-4 lg:grid-cols-[1.1fr_0.9fr]">
        <div className="space-y-4">
          <div className="flex items-center justify-between">
            <h2 className="text-lg font-semibold text-[#172033]">
              Matching Courses
            </h2>
            <span className="text-sm font-medium text-[#566176]">
              {courses.length} found
            </span>
          </div>

          {courses.length === 0 ? (
            <p className="rounded-md border border-dashed border-[#cbd5e1] bg-white p-5 text-sm text-[#566176]">
              No matching catalogue courses.
            </p>
          ) : (
            courses.map((course) => <CourseCard course={course} key={course.id} />)
          )}
        </div>

        <div className="rounded-md border border-[#dde4ef] bg-white p-5 shadow-sm">
          <h2 className="text-lg font-semibold text-[#172033]">
            Create Missing Course
          </h2>
          <p className="mt-1 text-sm leading-6 text-[#566176]">
            Only approved class representatives can add global catalogue
            courses.
          </p>

          {!representativeReady ? (
            <p className="mt-5 rounded-md border border-[#f2cf82] bg-[#fffaf0] p-4 text-sm text-[#7a4b00]">
              You need an approved representative membership before creating
              catalogue courses.
            </p>
          ) : (
            <form className="mt-5 space-y-4" onSubmit={handleCreate}>
              {createError ? (
                <Alert
                  title="Could not create course"
                  message={createError.message}
                  items={createError.items}
                />
              ) : null}
              {success ? (
                <Alert type="success" title="Course created" message={success} />
              ) : null}

              {matchingCourses.length > 0 ? (
                <div className="rounded-md border border-[#dde4ef] bg-[#f8fafc] p-4">
                  <p className="text-sm font-semibold text-[#172033]">
                    Existing matching courses
                  </p>
                  <div className="mt-3 space-y-2">
                    {matchingCourses.map((course) => (
                      <p key={course.id} className="text-sm text-[#344056]">
                        {formatCourseTitle(course)}
                      </p>
                    ))}
                  </div>
                </div>
              ) : null}

              <FormField
                id="course-name"
                label="Course name"
                name="name"
                onChange={handleChange}
                placeholder="Database Systems"
                required
                value={form.name}
              />
              <FormField
                id="course-code"
                label="Course code"
                name="code"
                onChange={handleChange}
                placeholder="CS301"
                required
                value={form.code}
              />
              <TextAreaField
                id="course-description"
                label="Description"
                name="description"
                onChange={handleChange}
                placeholder="Optional catalogue description"
                value={form.description}
              />

              {hasExactMatch ? (
                <p className="rounded-md border border-[#f2cf82] bg-[#fffaf0] p-3 text-sm text-[#7a4b00]">
                  A course with this exact name or code is already visible above.
                </p>
              ) : null}

              <button
                type="submit"
                disabled={isSubmitting || hasExactMatch}
                className="inline-flex w-full items-center justify-center rounded-md bg-[#256f68] px-5 py-2.5 text-sm font-semibold text-white transition hover:bg-[#1f5d58] focus:outline-none focus:ring-2 focus:ring-[#256f68] focus:ring-offset-2 disabled:cursor-not-allowed disabled:bg-[#8ebbb5]"
              >
                {isSubmitting ? "Creating course..." : "Create course"}
              </button>
            </form>
          )}
        </div>
      </div>
    </section>
  );
}

export default CourseCataloguePage;
