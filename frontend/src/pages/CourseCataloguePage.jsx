import { useEffect, useMemo, useState } from "react";

import { listMyClassrooms } from "../api/classrooms.js";
import { addClassCourse, createCourse, listCourses } from "../api/courses.js";
import Alert from "../components/Alert.jsx";
import Button from "../components/Button.jsx";
import EmptyState from "../components/EmptyState.jsx";
import FormField from "../components/FormField.jsx";
import LoadingScreen from "../components/LoadingScreen.jsx";
import Modal from "../components/Modal.jsx";
import PageHeader from "../components/PageHeader.jsx";
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

function CourseCard({
  actionKey,
  canAdd,
  canSubmitAdd,
  course,
  onAddToClass,
}) {
  return (
    <div className="cf-card p-4">
      <div className="flex flex-col gap-3 lg:flex-row lg:items-center lg:justify-between">
        <div>
          <h2 className="text-base font-semibold text-slate-900">
            {course.name}
          </h2>
          <p className="mt-1 text-sm font-medium text-cyan-700">{course.code}</p>
          {course.description ? (
            <p className="mt-2 max-w-3xl text-sm leading-6 text-slate-500">
              {course.description}
            </p>
          ) : null}
        </div>

        {canAdd ? (
          <div>
            <Button
              disabled={!canSubmitAdd || actionKey === `add:${course.id}`}
              onClick={() => onAddToClass(course)}
              variant="primary"
            >
              {actionKey === `add:${course.id}` ? "Adding..." : "Add to class"}
            </Button>
          </div>
        ) : null}
      </div>
    </div>
  );
}

function CourseCataloguePage() {
  const [search, setSearch] = useState("");
  const [courses, setCourses] = useState([]);
  const [matchingCourses, setMatchingCourses] = useState([]);
  const [representativeClassrooms, setRepresentativeClassrooms] = useState([]);
  const [selectedClassId, setSelectedClassId] = useState("");
  const [createOpen, setCreateOpen] = useState(false);
  const [isLoading, setIsLoading] = useState(true);
  const [isSearching, setIsSearching] = useState(false);
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [actionKey, setActionKey] = useState("");
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
        const managedClassrooms = classrooms.filter((classroom) =>
          isRepresentative(classroom.membership),
        );
        setCourses(courseData);
        setRepresentativeClassrooms(managedClassrooms);
        if (managedClassrooms.length === 1) {
          setSelectedClassId(String(managedClassrooms[0].id));
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
      setCreateOpen(false);
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

  async function handleAddToClass(course) {
    setActionKey(`add:${course.id}`);
    setError(null);
    setSuccess("");

    try {
      await addClassCourse(Number(selectedClassId), {
        course_id: course.id,
        instructor_name: null,
        is_default: false,
      });
      setSuccess(`${formatCourseTitle(course)} was added to the selected class.`);
    } catch (apiError) {
      setError(parseApiError(apiError));
    } finally {
      setActionKey("");
    }
  }

  if (isLoading) {
    return <LoadingScreen message="Loading course catalogue..." />;
  }

  return (
    <section className="space-y-6">
      <PageHeader
        actions={
          representativeClassrooms.length > 0 ? (
            <Button onClick={() => setCreateOpen(true)} variant="primary">
              Create missing course
            </Button>
          ) : null
        }
        description="Search reusable courses by name or code before creating a missing entry."
        eyebrow="Catalogue"
        title="Course Catalogue"
      />

      {error ? (
        <Alert
          title="Course action failed"
          message={error.message}
          items={error.items}
        />
      ) : null}
      {success ? <Alert type="success" title="Updated" message={success} /> : null}

      <form className="cf-card p-4" onSubmit={handleSearch}>
        <div className="grid gap-3 lg:grid-cols-[minmax(0,1fr)_260px_auto] lg:items-end">
          <div className="flex-1">
            <FormField
              id="catalogue-search"
              label="Search by course name or code"
              name="search"
              onChange={(event) => setSearch(event.target.value)}
              placeholder="Database Systems or CS101"
              value={search}
            />
          </div>
          {representativeClassrooms.length > 0 ? (
            <div>
              <label htmlFor="catalogue-target-class" className="cf-label">
                Add to class
              </label>
              <select
                className="cf-input"
                id="catalogue-target-class"
                onChange={(event) => setSelectedClassId(event.target.value)}
                value={selectedClassId}
              >
                <option value="">Choose class</option>
                {representativeClassrooms.map((classroom) => (
                  <option key={classroom.id} value={classroom.id}>
                    {classroom.name}
                  </option>
                ))}
              </select>
            </div>
          ) : null}
          <Button disabled={isSearching} type="submit" variant="primary">
            {isSearching ? "Searching..." : "Search"}
          </Button>
        </div>
      </form>

      <div className="flex items-center justify-between">
        <h2 className="text-base font-semibold text-slate-900">Results</h2>
        <span className="text-sm text-slate-500">{courses.length} found</span>
      </div>

      {courses.length === 0 ? (
        <EmptyState
          action={
            representativeClassrooms.length > 0 ? (
              <Button onClick={() => setCreateOpen(true)} variant="primary">
                Create missing course
              </Button>
            ) : null
          }
          message="Try a different name or code. Representatives can create a missing course after checking for duplicates."
          title="No matching courses"
        />
      ) : (
        <div className="space-y-3">
          {courses.map((course) => (
            <CourseCard
              actionKey={actionKey}
              canAdd={representativeClassrooms.length > 0}
              canSubmitAdd={Boolean(selectedClassId)}
              course={course}
              key={course.id}
              onAddToClass={handleAddToClass}
            />
          ))}
        </div>
      )}

      <Modal
        description="Existing matches stay visible so duplicates are easy to avoid."
        isOpen={createOpen}
        onClose={() => setCreateOpen(false)}
        title="Create missing course"
      >
        <form className="space-y-4" onSubmit={handleCreate}>
          {createError ? (
            <Alert
              title="Could not create course"
              message={createError.message}
              items={createError.items}
            />
          ) : null}

          {matchingCourses.length > 0 ? (
            <div className="rounded-lg border border-amber-200 bg-amber-50 p-4">
              <p className="text-sm font-semibold text-amber-800">
                Existing matching courses
              </p>
              <div className="mt-3 space-y-1">
                {matchingCourses.map((course) => (
                  <p key={course.id} className="text-sm text-amber-800">
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
            rows={3}
            value={form.description}
          />

          {hasExactMatch ? (
            <Alert
              message="A course with this exact name or code is already visible in the results."
              title="Possible duplicate"
              type="warning"
            />
          ) : null}

          <div className="flex flex-col-reverse gap-2 sm:flex-row sm:justify-end">
            <Button onClick={() => setCreateOpen(false)}>Cancel</Button>
            <Button
              disabled={isSubmitting || hasExactMatch}
              type="submit"
              variant="primary"
            >
              {isSubmitting ? "Creating..." : "Create course"}
            </Button>
          </div>
        </form>
      </Modal>
    </section>
  );
}

export default CourseCataloguePage;
