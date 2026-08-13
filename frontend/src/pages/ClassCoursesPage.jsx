import { useCallback, useEffect, useMemo, useState } from "react";
import { Link, useParams } from "react-router-dom";

import { listMyClassrooms } from "../api/classrooms.js";
import {
  addClassCourse,
  createCourse,
  deleteClassCourse,
  listClassCourses,
  listCourses,
  updateClassCourse,
} from "../api/courses.js";
import Alert from "../components/Alert.jsx";
import CheckboxField from "../components/CheckboxField.jsx";
import FormField from "../components/FormField.jsx";
import LoadingScreen from "../components/LoadingScreen.jsx";
import StatusBadge from "../components/StatusBadge.jsx";
import TextAreaField from "../components/TextAreaField.jsx";
import { isApproved, isRepresentative } from "../utils/classrooms.js";
import {
  formatCourseTitle,
  normalizeCourseCode,
  normalizeCourseName,
} from "../utils/courses.js";
import { parseApiError } from "../utils/errors.js";

const initialCourseForm = {
  name: "",
  code: "",
  description: "",
};

const initialAttachForm = {
  instructor_name: "",
  is_default: false,
};

function ClassCourseEditor({
  canManage,
  classCourse,
  onDelete,
  onUpdate,
  actionKey,
  confirmDeleteId,
  setConfirmDeleteId,
}) {
  const [form, setForm] = useState({
    instructor_name: classCourse.instructor_name || "",
    is_default: classCourse.is_default,
    is_active: classCourse.is_active,
  });

  const isBusy = actionKey?.endsWith(`:${classCourse.id}`);

  function handleTextChange(event) {
    const { name, value } = event.target;
    setForm((current) => ({ ...current, [name]: value }));
  }

  function handleCheckedChange(event) {
    const { name, checked } = event.target;
    setForm((current) => ({ ...current, [name]: checked }));
  }

  return (
    <div className="rounded-md border border-[#dde4ef] bg-white p-5 shadow-sm">
      <div className="flex flex-col gap-3 lg:flex-row lg:items-start lg:justify-between">
        <div>
          <h2 className="text-lg font-semibold text-[#172033]">
            {classCourse.course.name}
          </h2>
          <p className="mt-1 text-sm font-medium text-[#256f68]">
            {classCourse.course.code}
          </p>
          {classCourse.course.description ? (
            <p className="mt-3 max-w-2xl text-sm leading-6 text-[#566176]">
              {classCourse.course.description}
            </p>
          ) : null}
        </div>
        <div className="flex flex-wrap gap-2">
          <StatusBadge value={classCourse.is_default ? "default" : "optional"} />
          <StatusBadge value={classCourse.is_active ? "active" : "inactive"} />
        </div>
      </div>

      {!canManage ? (
        <dl className="mt-5 grid gap-4 sm:grid-cols-2">
          <div>
            <dt className="text-xs font-semibold uppercase tracking-wide text-[#667085]">
              Instructor
            </dt>
            <dd className="mt-1 text-sm font-medium text-[#172033]">
              {classCourse.instructor_name || "Not set"}
            </dd>
          </div>
          <div>
            <dt className="text-xs font-semibold uppercase tracking-wide text-[#667085]">
              Type
            </dt>
            <dd className="mt-1 text-sm font-medium text-[#172033]">
              {classCourse.is_default ? "Default course" : "Optional course"}
            </dd>
          </div>
        </dl>
      ) : (
        <div className="mt-5 space-y-4 border-t border-[#e5eaf2] pt-5">
          <FormField
            id={`instructor-${classCourse.id}`}
            label="Instructor name"
            name="instructor_name"
            onChange={handleTextChange}
            placeholder="Instructor name"
            value={form.instructor_name}
          />
          <div className="grid gap-3 sm:grid-cols-2">
            <CheckboxField
              checked={form.is_default}
              helpText="Default active courses are registered automatically for approved members."
              id={`default-${classCourse.id}`}
              label="Default course"
              name="is_default"
              onChange={handleCheckedChange}
            />
            <CheckboxField
              checked={form.is_active}
              helpText="Inactive courses are hidden from students and registrations."
              id={`active-${classCourse.id}`}
              label="Active course"
              name="is_active"
              onChange={handleCheckedChange}
            />
          </div>

          <div className="flex flex-col gap-2 sm:flex-row sm:justify-end">
            {confirmDeleteId === classCourse.id ? (
              <div className="flex flex-wrap items-center gap-2 rounded-md border border-[#f5b5b5] bg-[#fff8f8] p-2">
                <span className="text-sm font-medium text-[#7f1d1d]">
                  Deactivate?
                </span>
                <button
                  type="button"
                  disabled={isBusy}
                  onClick={() => onDelete(classCourse.id)}
                  className="rounded-md bg-[#b42318] px-3 py-1.5 text-sm font-semibold text-white transition hover:bg-[#971c14] focus:outline-none focus:ring-2 focus:ring-[#b42318] focus:ring-offset-2 disabled:cursor-not-allowed disabled:opacity-60"
                >
                  {actionKey === `delete:${classCourse.id}` ? "Saving..." : "Yes"}
                </button>
                <button
                  type="button"
                  disabled={isBusy}
                  onClick={() => setConfirmDeleteId(null)}
                  className="rounded-md border border-[#cbd5e1] px-3 py-1.5 text-sm font-semibold text-[#344056] transition hover:bg-white focus:outline-none focus:ring-2 focus:ring-[#256f68] focus:ring-offset-2"
                >
                  Cancel
                </button>
              </div>
            ) : (
              <button
                type="button"
                onClick={() => setConfirmDeleteId(classCourse.id)}
                className="rounded-md border border-[#f5b5b5] px-4 py-2 text-sm font-semibold text-[#7f1d1d] transition hover:bg-[#fff1f1] focus:outline-none focus:ring-2 focus:ring-[#b42318] focus:ring-offset-2"
              >
                Deactivate
              </button>
            )}
            <button
              type="button"
              disabled={isBusy}
              onClick={() =>
                onUpdate(classCourse.id, {
                  instructor_name: form.instructor_name.trim() || null,
                  is_default: form.is_default,
                  is_active: form.is_active,
                })
              }
              className="rounded-md bg-[#256f68] px-4 py-2 text-sm font-semibold text-white transition hover:bg-[#1f5d58] focus:outline-none focus:ring-2 focus:ring-[#256f68] focus:ring-offset-2 disabled:cursor-not-allowed disabled:bg-[#8ebbb5]"
            >
              {actionKey === `update:${classCourse.id}` ? "Saving..." : "Save"}
            </button>
          </div>
        </div>
      )}
    </div>
  );
}

function ClassCoursesPage() {
  const { classId } = useParams();
  const numericClassId = Number(classId);
  const [classroom, setClassroom] = useState(null);
  const [membership, setMembership] = useState(null);
  const [classCourses, setClassCourses] = useState([]);
  const [catalogueResults, setCatalogueResults] = useState([]);
  const [selectedCourse, setSelectedCourse] = useState(null);
  const [search, setSearch] = useState("");
  const [hasSearchedCatalogue, setHasSearchedCatalogue] = useState(false);
  const [courseForm, setCourseForm] = useState(initialCourseForm);
  const [attachForm, setAttachForm] = useState(initialAttachForm);
  const [isLoading, setIsLoading] = useState(true);
  const [isSearching, setIsSearching] = useState(false);
  const [isCreating, setIsCreating] = useState(false);
  const [isAttaching, setIsAttaching] = useState(false);
  const [actionKey, setActionKey] = useState("");
  const [confirmDeleteId, setConfirmDeleteId] = useState(null);
  const [error, setError] = useState(null);
  const [actionError, setActionError] = useState(null);
  const [success, setSuccess] = useState("");

  const canManage = useMemo(() => isRepresentative(membership), [membership]);
  const canViewCourses = useMemo(() => isApproved(membership), [membership]);

  const loadClassCourses = useCallback(async () => {
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
        return;
      }

      const data = await listClassCourses(
        numericClassId,
        isRepresentative(mineRecord.membership),
      );
      setClassCourses(data);
    } catch (apiError) {
      setError(parseApiError(apiError));
    }
  }, [numericClassId]);

  useEffect(() => {
    let isMounted = true;

    async function load() {
      await loadClassCourses();
      if (isMounted) {
        setIsLoading(false);
      }
    }

    load();

    return () => {
      isMounted = false;
    };
  }, [loadClassCourses]);

  function handleCourseFormChange(event) {
    const { name, value } = event.target;
    setCourseForm((current) => ({ ...current, [name]: value }));
  }

  function handleAttachTextChange(event) {
    const { name, value } = event.target;
    setAttachForm((current) => ({ ...current, [name]: value }));
  }

  function handleAttachCheckedChange(event) {
    const { name, checked } = event.target;
    setAttachForm((current) => ({ ...current, [name]: checked }));
  }

  async function handleSearch(event) {
    event.preventDefault();
    setIsSearching(true);
    setActionError(null);
    setSuccess("");

    try {
      const data = await listCourses(search.trim());
      setCatalogueResults(data);
      setSelectedCourse(null);
      setHasSearchedCatalogue(true);
    } catch (apiError) {
      setActionError(parseApiError(apiError));
    } finally {
      setIsSearching(false);
    }
  }

  async function handleCreateCourse(event) {
    event.preventDefault();
    setIsCreating(true);
    setActionError(null);
    setSuccess("");

    try {
      const payload = {
        name: normalizeCourseName(courseForm.name),
        code: normalizeCourseCode(courseForm.code),
      };
      const description = courseForm.description.trim();
      if (description) {
        payload.description = description;
      }

      const created = await createCourse(payload);
      setCatalogueResults((current) => [created, ...current]);
      setSelectedCourse(created);
      setCourseForm(initialCourseForm);
      setSuccess(`${formatCourseTitle(created)} was created and selected.`);
    } catch (apiError) {
      const parsed = parseApiError(apiError);
      setActionError(parsed);

      if (apiError.response?.status === 409) {
        const [codeMatches, nameMatches] = await Promise.all([
          courseForm.code.trim()
            ? listCourses(courseForm.code.trim())
            : Promise.resolve([]),
          courseForm.name.trim()
            ? listCourses(courseForm.name.trim())
            : Promise.resolve([]),
        ]);
      const uniqueMatches = [...codeMatches, ...nameMatches].filter(
        (course, index, all) =>
          all.findIndex((item) => item.id === course.id) === index,
      );
      setCatalogueResults(uniqueMatches);
      setHasSearchedCatalogue(true);
      }
    } finally {
      setIsCreating(false);
    }
  }

  async function handleAttach(event) {
    event.preventDefault();

    if (!selectedCourse) {
      setActionError({
        message: "Select a catalogue course before adding it to the class.",
        items: [],
      });
      return;
    }

    setIsAttaching(true);
    setActionError(null);
    setSuccess("");

    try {
      const added = await addClassCourse(numericClassId, {
        course_id: selectedCourse.id,
        instructor_name: attachForm.instructor_name.trim() || null,
        is_default: attachForm.is_default,
      });
      setSuccess(`${formatCourseTitle(added.course)} was added to this class.`);
      setSelectedCourse(null);
      setAttachForm(initialAttachForm);
      await loadClassCourses();
    } catch (apiError) {
      setActionError(parseApiError(apiError));
    } finally {
      setIsAttaching(false);
    }
  }

  async function handleUpdate(classCourseId, payload) {
    setActionKey(`update:${classCourseId}`);
    setActionError(null);
    setSuccess("");

    try {
      const updated = await updateClassCourse(classCourseId, payload);
      setSuccess(`${formatCourseTitle(updated.course)} was updated.`);
      await loadClassCourses();
    } catch (apiError) {
      setActionError(parseApiError(apiError));
    } finally {
      setActionKey("");
    }
  }

  async function handleDelete(classCourseId) {
    setActionKey(`delete:${classCourseId}`);
    setActionError(null);
    setSuccess("");

    try {
      await deleteClassCourse(classCourseId);
      setConfirmDeleteId(null);
      setSuccess("Class course was deactivated.");
      await loadClassCourses();
    } catch (apiError) {
      setActionError(parseApiError(apiError));
    } finally {
      setActionKey("");
    }
  }

  if (isLoading) {
    return <LoadingScreen message="Loading class courses..." />;
  }

  if (error && !classroom) {
    return (
      <section className="space-y-5">
        <Alert
          title="Could not load class courses"
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
            Classroom courses
          </p>
          <h1 className="mt-2 text-3xl font-bold text-[#172033]">
            {classroom?.name}
          </h1>
          <p className="mt-3 max-w-2xl text-base leading-7 text-[#566176]">
            Manage catalogue courses attached to this classroom.
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
            to={`/classes/${numericClassId}/my-courses`}
            className="rounded-md border border-[#cbd5e1] px-4 py-2 text-sm font-semibold text-[#344056] transition hover:bg-white focus:outline-none focus:ring-2 focus:ring-[#256f68] focus:ring-offset-2"
          >
            My courses
          </Link>
        </div>
      </div>

      {error ? (
        <Alert title="Course access blocked" message={error.message} items={error.items} />
      ) : null}

      {!canViewCourses ? (
        <div className="rounded-md border border-[#f2cf82] bg-[#fffaf0] p-5">
          <h2 className="text-lg font-semibold text-[#172033]">
            Membership {membership?.status}
          </h2>
          <p className="mt-2 text-sm leading-6 text-[#7a4b00]">
            Class courses are available after your membership is approved.
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

          {canManage ? (
            <div className="rounded-md border border-[#dde4ef] bg-white p-5 shadow-sm sm:p-6">
              <h2 className="text-lg font-semibold text-[#172033]">
                Add Catalogue Course
              </h2>
              <div className="mt-5 grid gap-6 lg:grid-cols-[1fr_1fr]">
                <div className="space-y-4">
                  <form onSubmit={handleSearch}>
                    <div className="flex flex-col gap-3 sm:flex-row">
                      <div className="flex-1">
                        <FormField
                          id="class-course-search"
                          label="Search catalogue"
                          name="search"
                          onChange={(event) => setSearch(event.target.value)}
                          placeholder="Course name or code"
                          value={search}
                        />
                      </div>
                      <button
                        type="submit"
                        disabled={isSearching}
                        className="mt-6 rounded-md bg-[#256f68] px-4 py-2.5 text-sm font-semibold text-white transition hover:bg-[#1f5d58] focus:outline-none focus:ring-2 focus:ring-[#256f68] focus:ring-offset-2 disabled:cursor-not-allowed disabled:bg-[#8ebbb5] sm:self-start"
                      >
                        {isSearching ? "Searching..." : "Search"}
                      </button>
                    </div>
                  </form>

                  <div className="space-y-2">
                    {catalogueResults.length === 0 ? (
                      <p className="rounded-md border border-dashed border-[#cbd5e1] p-4 text-sm text-[#566176]">
                        Search for an existing course first.
                      </p>
                    ) : (
                      catalogueResults.map((course) => (
                        <button
                          type="button"
                          key={course.id}
                          onClick={() => setSelectedCourse(course)}
                          className={`w-full rounded-md border p-3 text-left transition focus:outline-none focus:ring-2 focus:ring-[#256f68] focus:ring-offset-2 ${
                            selectedCourse?.id === course.id
                              ? "border-[#256f68] bg-[#ecfdf7]"
                              : "border-[#dde4ef] hover:border-[#aac7c2]"
                          }`}
                        >
                          <span className="block text-sm font-semibold text-[#172033]">
                            {formatCourseTitle(course)}
                          </span>
                          {course.description ? (
                            <span className="mt-1 block text-sm text-[#566176]">
                              {course.description}
                            </span>
                          ) : null}
                        </button>
                      ))
                    )}
                  </div>
                </div>

                <div className="space-y-5">
                  <form className="space-y-4" onSubmit={handleAttach}>
                    <div className="rounded-md border border-[#dde4ef] bg-[#f8fafc] p-4">
                      <p className="text-sm font-semibold text-[#172033]">
                        Selected course
                      </p>
                      <p className="mt-1 text-sm text-[#566176]">
                        {selectedCourse
                          ? formatCourseTitle(selectedCourse)
                          : "No course selected"}
                      </p>
                    </div>
                    <FormField
                      id="attach-instructor"
                      label="Instructor name"
                      name="instructor_name"
                      onChange={handleAttachTextChange}
                      placeholder="Instructor name"
                      value={attachForm.instructor_name}
                    />
                    <CheckboxField
                      checked={attachForm.is_default}
                      helpText="Approved members are automatically registered in active default courses."
                      id="attach-default"
                      label="Default course"
                      name="is_default"
                      onChange={handleAttachCheckedChange}
                    />
                    <button
                      type="submit"
                      disabled={isAttaching}
                      className="inline-flex w-full items-center justify-center rounded-md bg-[#256f68] px-5 py-2.5 text-sm font-semibold text-white transition hover:bg-[#1f5d58] focus:outline-none focus:ring-2 focus:ring-[#256f68] focus:ring-offset-2 disabled:cursor-not-allowed disabled:bg-[#8ebbb5]"
                    >
                      {isAttaching ? "Adding..." : "Add to class"}
                    </button>
                  </form>

                  <form
                    className="space-y-4 border-t border-[#e5eaf2] pt-5"
                    onSubmit={handleCreateCourse}
                  >
                    <h3 className="text-base font-semibold text-[#172033]">
                      Create missing catalogue course
                    </h3>
                    <FormField
                      id="missing-course-name"
                      label="Course name"
                      name="name"
                      onChange={handleCourseFormChange}
                      required
                      value={courseForm.name}
                    />
                    <FormField
                      id="missing-course-code"
                      label="Course code"
                      name="code"
                      onChange={handleCourseFormChange}
                      required
                      value={courseForm.code}
                    />
                    <TextAreaField
                      id="missing-course-description"
                      label="Description"
                      name="description"
                      onChange={handleCourseFormChange}
                      value={courseForm.description}
                    />
                    {!hasSearchedCatalogue ? (
                      <p className="rounded-md border border-[#f2cf82] bg-[#fffaf0] p-3 text-sm text-[#7a4b00]">
                        Search the catalogue before creating a missing course.
                      </p>
                    ) : null}
                    {hasSearchedCatalogue && catalogueResults.length > 0 ? (
                      <p className="rounded-md border border-[#f2cf82] bg-[#fffaf0] p-3 text-sm text-[#7a4b00]">
                        Select one of the matching catalogue courses above, or
                        refine the search until no existing course matches.
                      </p>
                    ) : null}
                    <button
                      type="submit"
                      disabled={
                        isCreating ||
                        !hasSearchedCatalogue ||
                        catalogueResults.length > 0
                      }
                      className="inline-flex w-full items-center justify-center rounded-md border border-[#cbd5e1] px-5 py-2.5 text-sm font-semibold text-[#344056] transition hover:border-[#8ea0b8] hover:bg-[#f8fafc] focus:outline-none focus:ring-2 focus:ring-[#256f68] focus:ring-offset-2 disabled:cursor-not-allowed disabled:opacity-60"
                    >
                      {isCreating ? "Creating..." : "Create and select"}
                    </button>
                  </form>
                </div>
              </div>
            </div>
          ) : null}

          <div className="space-y-4">
            <div className="flex items-center justify-between">
              <h2 className="text-lg font-semibold text-[#172033]">
                Class Course List
              </h2>
              <span className="text-sm font-medium text-[#566176]">
                {classCourses.length} courses
              </span>
            </div>

            {classCourses.length === 0 ? (
              <p className="rounded-md border border-dashed border-[#cbd5e1] bg-white p-5 text-sm text-[#566176]">
                No courses have been added to this class yet.
              </p>
            ) : (
              classCourses.map((classCourse) => (
                <ClassCourseEditor
                  actionKey={actionKey}
                  canManage={canManage}
                  classCourse={classCourse}
                  confirmDeleteId={confirmDeleteId}
                  key={classCourse.id}
                  onDelete={handleDelete}
                  onUpdate={handleUpdate}
                  setConfirmDeleteId={setConfirmDeleteId}
                />
              ))
            )}
          </div>
        </>
      )}
    </section>
  );
}

export default ClassCoursesPage;
