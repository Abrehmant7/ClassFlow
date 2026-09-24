import { useState } from "react";

import useContentAction from "../hooks/useContentAction.js";
import Alert from "./Alert.jsx";
import Button from "./Button.jsx";
import CheckboxField from "./CheckboxField.jsx";
import ClassContentScopeField from "./ClassContentScopeField.jsx";
import FormField from "./FormField.jsx";
import Modal from "./Modal.jsx";
import TextAreaField from "./TextAreaField.jsx";

function AnnouncementForm({ announcement, courses, onClose, onSave }) {
  const [form, setForm] = useState({
    title: announcement?.title || "",
    body: announcement?.body || "",
    class_course_id: announcement?.class_course_id ?? "",
    is_pinned: announcement?.is_pinned || false,
  });
  const { busy, error, setError, run } = useContentAction();

  function change(event) {
    const { name, value, type, checked } = event.target;
    setForm((current) => ({ ...current, [name]: type === "checkbox" ? checked : value }));
  }

  function submit(event) {
    event.preventDefault();
    if (!form.title.trim() || !form.body.trim() || form.title.length > 200) {
      setError({ message: "Enter a title of up to 200 characters and an announcement body.", items: [] });
      return;
    }
    run(() => onSave({
      title: form.title.trim(), body: form.body.trim(), is_pinned: form.is_pinned,
      class_course_id: form.class_course_id ? Number(form.class_course_id) : null,
    }));
  }

  return (
    <Modal isOpen isBusy={busy} onClose={onClose} title={announcement ? "Edit announcement" : "New announcement"}>
      <form className="space-y-4" onSubmit={submit}>
        <fieldset className="min-w-0 space-y-4" disabled={busy}>
          <FormField id="announcement-title" label="Title" name="title" maxLength={200}
            required onChange={change} value={form.title} helpText="Maximum 200 characters." />
          <TextAreaField id="announcement-body" label="Body" name="body" required
            onChange={change} value={form.body} rows={6} />
          <ClassContentScopeField id="announcement-scope" courses={courses}
            value={form.class_course_id} onChange={change} />
          <CheckboxField id="announcement-pinned" label="Pinned announcement" name="is_pinned"
            checked={form.is_pinned} onChange={change} helpText="Pinned announcements appear first." />
        </fieldset>
        {error ? <Alert title="Could not save announcement" {...error} /> : null}
        <div className="flex flex-col-reverse gap-2 sm:flex-row sm:justify-end">
          <Button disabled={busy} onClick={onClose}>Cancel</Button>
          <Button disabled={busy} type="submit" variant="primary">
            {busy ? "Saving..." : announcement ? "Save changes" : "Create announcement"}
          </Button>
        </div>
      </form>
    </Modal>
  );
}

export default AnnouncementForm;
