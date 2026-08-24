import { useEffect, useState } from "react";

import Alert from "./Alert.jsx";
import Button from "./Button.jsx";
import FormField from "./FormField.jsx";
import Modal from "./Modal.jsx";
import TextAreaField from "./TextAreaField.jsx";
import { formatCourseTitle } from "../utils/courses.js";
import { TASK_PRIORITIES, TASK_TYPES, toApiDeadline } from "../utils/tasks.js";

const initialTaskForm = {
  title: "",
  description: "",
  class_course_id: "",
  task_type: "other",
  priority: "medium",
  deadline: "",
};

function SelectField({ children, id, label, name, onChange, value }) {
  return (
    <div>
      <label htmlFor={id} className="cf-label">
        {label}
      </label>
      <select
        className="cf-input"
        id={id}
        name={name}
        onChange={onChange}
        value={value}
      >
        {children}
      </select>
    </div>
  );
}

function SharedTaskModal({
  activeClassCourses,
  error,
  isOpen,
  isSubmitting,
  onClose,
  onCreate,
}) {
  const [form, setForm] = useState(initialTaskForm);

  useEffect(() => {
    if (!isOpen) {
      setForm(initialTaskForm);
    }
  }, [isOpen]);

  function handleChange(event) {
    const { name, value } = event.target;
    setForm((current) => ({ ...current, [name]: value }));
  }

  async function handleSubmit(event) {
    event.preventDefault();

    const payload = {
      title: form.title.trim(),
      visibility: "shared",
      task_type: form.task_type,
      priority: form.priority,
      class_course_id: form.class_course_id
        ? Number(form.class_course_id)
        : null,
      deadline: toApiDeadline(form.deadline),
    };

    const description = form.description.trim();
    if (description) {
      payload.description = description;
    }

    const created = await onCreate(payload);
    if (created) {
      setForm(initialTaskForm);
      onClose();
    }
  }

  return (
    <Modal
      description="Shared tasks are visible to approved members according to the backend course and membership rules."
      isOpen={isOpen}
      onClose={onClose}
      title="Create shared task"
    >
      <form className="space-y-4" onSubmit={handleSubmit}>
        <FormField
          id="task-title"
          label="Title"
          name="title"
          onChange={handleChange}
          required
          value={form.title}
        />
        <div className="grid gap-4 sm:grid-cols-2">
          <SelectField
            id="task-course"
            label="Course"
            name="class_course_id"
            onChange={handleChange}
            value={form.class_course_id}
          >
            <option value="">Class-wide</option>
            {activeClassCourses.map((classCourse) => (
              <option key={classCourse.id} value={classCourse.id}>
                {formatCourseTitle(classCourse.course)}
              </option>
            ))}
          </SelectField>
          <SelectField
            id="task-priority"
            label="Priority"
            name="priority"
            onChange={handleChange}
            value={form.priority}
          >
            {TASK_PRIORITIES.map((priority) => (
              <option key={priority} value={priority}>
                {priority}
              </option>
            ))}
          </SelectField>
          <SelectField
            id="task-type"
            label="Task type"
            name="task_type"
            onChange={handleChange}
            value={form.task_type}
          >
            {TASK_TYPES.map((type) => (
              <option key={type} value={type}>
                {type}
              </option>
            ))}
          </SelectField>
          <FormField
            id="task-deadline"
            label="Deadline"
            name="deadline"
            onChange={handleChange}
            type="datetime-local"
            value={form.deadline}
          />
        </div>
        <TextAreaField
          id="task-description"
          label="Description"
          name="description"
          onChange={handleChange}
          rows={3}
          value={form.description}
        />

        {error ? (
          <Alert
            title="Could not create task"
            message={error.message}
            items={error.items}
          />
        ) : null}

        <div className="flex flex-col-reverse gap-2 sm:flex-row sm:justify-end">
          <Button onClick={onClose}>Cancel</Button>
          <Button disabled={isSubmitting} type="submit" variant="primary">
            {isSubmitting ? "Creating..." : "Create task"}
          </Button>
        </div>
      </form>
    </Modal>
  );
}

export default SharedTaskModal;
