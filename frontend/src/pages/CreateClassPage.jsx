import { useState } from "react";
import { Link, useNavigate } from "react-router-dom";

import { createClassroom } from "../api/classrooms.js";
import Alert from "../components/Alert.jsx";
import Button from "../components/Button.jsx";
import FormField from "../components/FormField.jsx";
import PageHeader from "../components/PageHeader.jsx";
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
      <PageHeader
        description="Creating a class makes you its approved representative."
        eyebrow="New class"
        title="Create Class"
      />

      <form
        className="cf-card p-5 sm:p-6"
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
              className="text-sm font-semibold text-blue-700 hover:text-blue-900 cf-focus"
            >
              Back to classes
            </Link>
            <Button disabled={isSubmitting} type="submit" variant="primary">
              {isSubmitting ? "Creating class..." : "Create class"}
            </Button>
          </div>
        </div>
      </form>
    </section>
  );
}

export default CreateClassPage;
