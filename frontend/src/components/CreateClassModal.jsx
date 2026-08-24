import { useEffect, useState } from "react";

import { createClassroom } from "../api/classrooms.js";
import Alert from "./Alert.jsx";
import Button from "./Button.jsx";
import FormField from "./FormField.jsx";
import Modal from "./Modal.jsx";
import TextAreaField from "./TextAreaField.jsx";
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

function CreateClassModal({ isOpen, onClose, onCreated }) {
  const [form, setForm] = useState(initialForm);
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [error, setError] = useState(null);

  useEffect(() => {
    if (!isOpen) {
      setForm(initialForm);
      setError(null);
    }
  }, [isOpen]);

  function handleChange(event) {
    const { name, value } = event.target;
    setForm((current) => ({ ...current, [name]: value }));
  }

  async function handleSubmit(event) {
    event.preventDefault();
    setIsSubmitting(true);
    setError(null);

    try {
      const classroom = await createClassroom(buildPayload(form));
      onCreated(classroom);
      onClose();
    } catch (apiError) {
      setError(parseApiError(apiError));
    } finally {
      setIsSubmitting(false);
    }
  }

  return (
    <Modal
      description="Creating a class makes you its approved representative."
      isOpen={isOpen}
      onClose={onClose}
      title="Create class"
    >
      <form className="space-y-5" onSubmit={handleSubmit}>
        {error ? (
          <Alert
            title="Could not create class"
            message={error.message}
            items={error.items}
          />
        ) : null}

        <FormField
          id="class-modal-name"
          label="Class name"
          name="name"
          onChange={handleChange}
          placeholder="BS Computer Science"
          required
          value={form.name}
        />

        <div className="grid gap-4 sm:grid-cols-2">
          <FormField
            id="class-modal-semester"
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
            id="class-modal-section"
            label="Section"
            name="section"
            onChange={handleChange}
            placeholder="A"
            required
            value={form.section}
          />
        </div>

        <TextAreaField
          id="class-modal-description"
          label="Description"
          name="description"
          onChange={handleChange}
          placeholder="Optional notes about this class"
          value={form.description}
        />

        <div className="flex flex-col-reverse gap-2 sm:flex-row sm:justify-end">
          <Button onClick={onClose}>Cancel</Button>
          <Button disabled={isSubmitting} type="submit" variant="primary">
            {isSubmitting ? "Creating..." : "Create class"}
          </Button>
        </div>
      </form>
    </Modal>
  );
}

export default CreateClassModal;
