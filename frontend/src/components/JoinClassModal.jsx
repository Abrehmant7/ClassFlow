import { useEffect, useState } from "react";

import { joinClassroom } from "../api/classrooms.js";
import Alert from "./Alert.jsx";
import Button from "./Button.jsx";
import FormField from "./FormField.jsx";
import Modal from "./Modal.jsx";
import { parseApiError } from "../utils/errors.js";

const initialForm = {
  class_id: "",
  join_code: "",
};

function JoinClassModal({ isOpen, onClose, onJoined }) {
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
      const membership = await joinClassroom(
        Number(form.class_id),
        form.join_code.trim().toUpperCase(),
      );
      onJoined(membership);
      onClose();
    } catch (apiError) {
      setError(parseApiError(apiError));
    } finally {
      setIsSubmitting(false);
    }
  }

  return (
    <Modal
      description="Use the class ID and join code shared by your representative."
      isOpen={isOpen}
      onClose={onClose}
      title="Join class"
    >
      <form className="space-y-5" onSubmit={handleSubmit}>
        {error ? (
          <Alert
            title="Could not request membership"
            message={error.message}
            items={error.items}
          />
        ) : null}

        <FormField
          id="join-modal-class-id"
          inputMode="numeric"
          label="Class ID"
          min="1"
          name="class_id"
          onChange={handleChange}
          required
          type="number"
          value={form.class_id}
        />
        <FormField
          autoComplete="off"
          helpText="Your request remains pending until a representative approves it."
          id="join-modal-code"
          label="Join code"
          name="join_code"
          onChange={handleChange}
          placeholder="ABC12345"
          required
          value={form.join_code}
        />

        <div className="flex flex-col-reverse gap-2 sm:flex-row sm:justify-end">
          <Button onClick={onClose}>Cancel</Button>
          <Button disabled={isSubmitting} type="submit" variant="primary">
            {isSubmitting ? "Requesting..." : "Request membership"}
          </Button>
        </div>
      </form>
    </Modal>
  );
}

export default JoinClassModal;
