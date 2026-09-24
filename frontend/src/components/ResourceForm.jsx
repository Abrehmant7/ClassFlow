import { useState } from "react";

import useContentAction from "../hooks/useContentAction.js";
import { contentScope, validateResourceFile } from "../utils/classContent.js";
import Alert from "./Alert.jsx";
import Button from "./Button.jsx";
import ClassContentScopeField from "./ClassContentScopeField.jsx";
import FormField from "./FormField.jsx";
import Modal from "./Modal.jsx";
import TextAreaField from "./TextAreaField.jsx";

function ResourceForm({ resource, courses, onClose, onSave }) {
  const [form, setForm] = useState({
    title: resource?.title || "", description: resource?.description || "", class_course_id: "",
  });
  const [file, setFile] = useState(null);
  const [progress, setProgress] = useState(null);
  const { busy, error, setError, run } = useContentAction();

  function change(event) {
    const { name, value } = event.target;
    setForm((current) => ({ ...current, [name]: value }));
  }

  function selectFile(event) {
    const selected = event.target.files?.[0] || null;
    setFile(selected);
    const message = validateResourceFile(selected);
    setError(message ? { message, items: [] } : null);
  }

  function submit(event) {
    event.preventDefault();
    const fileError = resource ? null : validateResourceFile(file);
    if (!form.title.trim() || form.title.length > 200 || fileError) {
      setError({ message: fileError || "Enter a title of up to 200 characters.", items: [] });
      return;
    }
    setProgress(null);
    const payload = { title: form.title.trim(), description: form.description.trim() || null };
    if (!resource) {
      payload.class_course_id = form.class_course_id ? Number(form.class_course_id) : null;
      payload.file = file;
    }
    run(() => onSave(payload, (event) => {
      if (event.total) setProgress(Math.min(100, Math.round(event.loaded * 100 / event.total)));
    }));
  }

  return (
    <Modal isOpen isBusy={busy} onClose={onClose} title={resource ? "Edit resource" : "Upload resource"}>
      <form className="space-y-4" onSubmit={submit}>
        <fieldset className="min-w-0 space-y-4" disabled={busy}>
          <FormField id="resource-title" label="Title" name="title" maxLength={200} required
            onChange={change} value={form.title} helpText="Maximum 200 characters." />
          <TextAreaField id="resource-description" label="Description" name="description"
            onChange={change} value={form.description} />
          {resource ? (
            <div className="space-y-1 break-words rounded-lg bg-slate-50 p-3 text-sm text-slate-600">
              <p>Scope: {contentScope(resource.class_course_id, courses)}</p>
              <p>PDF: {resource.file_name}</p>
              <p>The scope and PDF cannot be changed after upload.</p>
            </div>
          ) : (
            <>
              <ClassContentScopeField id="resource-scope" courses={courses}
                value={form.class_course_id} onChange={change} />
              <div>
                <label className="cf-label" htmlFor="resource-file">PDF file <span className="text-red-600">*</span></label>
                <input accept=".pdf,application/pdf" aria-describedby="resource-file-help" className="cf-input"
                  id="resource-file" type="file" required onChange={selectFile} />
                <p className="mt-1 text-xs text-slate-500" id="resource-file-help">
                  PDF only. Maximum 10 MB. The server validates the uploaded file.
                </p>
              </div>
            </>
          )}
        </fieldset>
        {busy && !resource ? (
          <div className="space-y-1 text-sm text-slate-600" role="status">
            {progress != null ? <progress aria-label="PDF upload progress" className="w-full" value={progress} max={100} /> : null}
            <p>{progress === 100 ? "Upload received. Preparing resource..." : progress == null ? "Uploading PDF..." : `Uploading PDF: ${progress}%`}</p>
          </div>
        ) : null}
        {error ? <Alert title={resource ? "Could not save resource" : "Upload failed"} {...error} /> : null}
        <div className="flex flex-col-reverse gap-2 sm:flex-row sm:justify-end">
          <Button disabled={busy} onClick={onClose}>Cancel</Button>
          <Button disabled={busy} type="submit" variant="primary">
            {busy ? "Saving..." : resource ? "Save changes" : "Upload PDF"}
          </Button>
        </div>
      </form>
    </Modal>
  );
}

export default ResourceForm;
