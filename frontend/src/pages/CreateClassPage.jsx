import { useState } from "react";
import { Link, useNavigate } from "react-router-dom";

import { createClassroom } from "../api/classrooms.js";
import Alert from "../components/Alert.jsx";
import FormField from "../components/FormField.jsx";
import TextAreaField from "../components/TextAreaField.jsx";
import { parseApiError } from "../utils/errors.js";

const initialForm = {
  name: "",
  semester: "",
  section: "",
  description: "",
};

function buildPayload(form) {
  const payload = {
    name: form.name.trim(),
    semester: Number(form.semester),
    section: form.section.trim(),
  };

  const description = form.description.trim();
  if (description) {
    payload.description = description;
  }

  return payload;
}

function CreateClassPage() {
  const navigate = useNavigate();
  const [form, setForm] = useState(initialForm);
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [error, setError] = useState(null);
  const [success, setSuccess] = useState("");

  function handleChange(event) {
    const { name, value } = event.target;
    setForm((current) => ({ ...current, [name]: value }));
  }

  async function handleSubmit(event) {
    event.preventDefault();
    setIsSubmitting(true);
    setError(null);
    setSuccess("");

    try {
      const classroom = await createClassroom(buildPayload(form));
      setSuccess(`Class created. Join code: ${classroom.join_code}`);
      window.setTimeout(() => {
        navigate(`/classes/${classroom.id}`, { replace: true });
      }, 500);
    } catch (apiError) {
      setError(parseApiError(apiError));
    } finally {
      setIsSubmitting(false);
    }
  }

  return (
    <section className="mx-auto max-w-4xl space-y-6">
      <div>
        <p className="text-sm font-semibold uppercase tracking-wide text-[#256f68]">
          New class
        </p>
        <h1 className="mt-2 text-3xl font-bold text-[#172033]">
          Create Class
        </h1>
        <p className="mt-3 max-w-2xl text-base leading-7 text-[#566176]">
          Creating a class makes you its approved representative.
        </p>
      </div>

      <form
        className="rounded-md border border-[#dde4ef] bg-white p-5 shadow-sm sm:p-6"
        onSubmit={handleSubmit}
      >
        <div className="space-y-5">
          {error ? (
            <Alert
              title="Could not create class"
              message={error.message}
              items={error.items}
            />
          ) : null}
          {success ? (
            <Alert type="success" title="Class created" message={success} />
          ) : null}

          <FormField
            id="class-name"
            label="Class name"
            name="name"
            onChange={handleChange}
            placeholder="BS Computer Science"
            required
            value={form.name}
          />

          <div className="grid gap-4 sm:grid-cols-2">
            <FormField
              id="class-semester"
              inputMode="numeric"
              label="Semester"
              min="1"
              name="semester"
              onChange={handleChange}
              required
              type="number"
              value={form.semester}
            />
            <FormField
              id="class-section"
              label="Section"
              name="section"
              onChange={handleChange}
              placeholder="A"
              required
              value={form.section}
            />
          </div>

          <TextAreaField
            id="class-description"
            label="Description"
            name="description"
            onChange={handleChange}
            placeholder="Optional notes about this class"
            value={form.description}
          />

          <div className="flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-between">
            <Link
              to="/classes"
              className="text-sm font-semibold text-[#256f68] hover:text-[#1f5d58]"
            >
              Back to classes
            </Link>
            <button
              type="submit"
              disabled={isSubmitting}
              className="inline-flex items-center justify-center rounded-md bg-[#256f68] px-5 py-2.5 text-sm font-semibold text-white transition hover:bg-[#1f5d58] focus:outline-none focus:ring-2 focus:ring-[#256f68] focus:ring-offset-2 disabled:cursor-not-allowed disabled:bg-[#8ebbb5]"
            >
              {isSubmitting ? "Creating class..." : "Create class"}
            </button>
          </div>
        </div>
      </form>
    </section>
  );
}

export default CreateClassPage;
