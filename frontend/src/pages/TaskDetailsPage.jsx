import { useCallback, useEffect, useState } from "react";
import { Link, useNavigate, useParams } from "react-router-dom";

import {
  deleteTask,
  deleteTaskAttachment,
  downloadTaskAttachment,
  getTask,
  updateTask,
  updateTaskProgress,
  uploadTaskAttachment,
} from "../api/tasks.js";
import Alert from "../components/Alert.jsx";
import FormField from "../components/FormField.jsx";
import LoadingScreen from "../components/LoadingScreen.jsx";
import StatusBadge from "../components/StatusBadge.jsx";
import TextAreaField from "../components/TextAreaField.jsx";
import { parseApiError } from "../utils/errors.js";
import {
  formatDeadline,
  formatFileSize,
  getCreatorName,
  TASK_PRIORITIES,
  TASK_TYPES,
  toApiDeadline,
  toDateTimeLocal,
} from "../utils/tasks.js";

function SelectField({ id, label, name, onChange, value, children }) {
  return (
    <div>
      <label htmlFor={id} className="block text-sm font-medium text-slate-600">
        {label}
      </label>
      <select
        className="mt-1 block w-full rounded-md border border-slate-200 bg-white px-3 py-2 text-slate-950 shadow-sm outline-none transition focus:border-blue-600 focus:ring-2 focus:ring-blue-600/20"
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

function buildEditForm(task) {
  return {
    title: task.title || "",
    description: task.description || "",
    task_type: task.task_type || "other",
    priority: task.priority || "medium",
    deadline: toDateTimeLocal(task.deadline),
    status: task.status || "active",
  };
}

function TaskDetailsPage() {
  const { taskId } = useParams();
  const numericTaskId = Number(taskId);
  const navigate = useNavigate();
  const [task, setTask] = useState(null);
  const [editForm, setEditForm] = useState(null);
  const [selectedFile, setSelectedFile] = useState(null);
  const [isLoading, setIsLoading] = useState(true);
  const [isSaving, setIsSaving] = useState(false);
  const [isUploading, setIsUploading] = useState(false);
  const [actionKey, setActionKey] = useState("");
  const [confirmDelete, setConfirmDelete] = useState(false);
  const [confirmAttachmentId, setConfirmAttachmentId] = useState(null);
  const [error, setError] = useState(null);
  const [actionError, setActionError] = useState(null);
  const [success, setSuccess] = useState("");

  const loadTask = useCallback(async () => {
    setError(null);
    setActionError(null);

    try {
      const data = await getTask(numericTaskId);
      setTask(data);
      setEditForm(buildEditForm(data));
    } catch (apiError) {
      setError(parseApiError(apiError));
    }
  }, [numericTaskId]);

  useEffect(() => {
    let isMounted = true;

    async function load() {
      await loadTask();
      if (isMounted) {
        setIsLoading(false);
      }
    }

    load();

    return () => {
      isMounted = false;
    };
  }, [loadTask]);

  function handleEditChange(event) {
    const { name, value } = event.target;
    setEditForm((current) => ({ ...current, [name]: value }));
  }

  async function handleProgress(nextStatus) {
    setActionKey(`progress:${nextStatus}`);
    setActionError(null);
    setSuccess("");

    try {
      const updated = await updateTaskProgress(numericTaskId, nextStatus);
      setTask(updated);
      setEditForm(buildEditForm(updated));
      setSuccess(
        nextStatus === "completed"
          ? "Task marked completed."
          : "Task marked pending.",
      );
    } catch (apiError) {
      setActionError(parseApiError(apiError));
    } finally {
      setActionKey("");
    }
  }

  async function handleStatus(status) {
    setActionKey(`status:${status}`);
    setActionError(null);
    setSuccess("");

    try {
      const updated = await updateTask(numericTaskId, { status });
      setTask(updated);
      setEditForm(buildEditForm(updated));
      setSuccess(`Task status changed to ${status}.`);
    } catch (apiError) {
      setActionError(parseApiError(apiError));
    } finally {
      setActionKey("");
    }
  }

  async function handleSave(event) {
    event.preventDefault();
    setIsSaving(true);
    setActionError(null);
    setSuccess("");

    try {
      const payload = {
        title: editForm.title.trim(),
        description: editForm.description.trim() || null,
        priority: editForm.priority,
        deadline: toApiDeadline(editForm.deadline),
      };

      if (task.visibility === "personal") {
        payload.task_type = editForm.task_type;
        payload.status = editForm.status;
      }

      const updated = await updateTask(numericTaskId, payload);
      setTask(updated);
      setEditForm(buildEditForm(updated));
      setSuccess("Task saved.");
    } catch (apiError) {
      setActionError(parseApiError(apiError));
    } finally {
      setIsSaving(false);
    }
  }

  async function handleDeleteTask() {
    setActionKey("delete-task");
    setActionError(null);
    setSuccess("");

    try {
      await deleteTask(numericTaskId);
      navigate(task.classroom_id ? `/classes/${task.classroom_id}` : "/dashboard", {
        replace: true,
      });
    } catch (apiError) {
      setActionError(parseApiError(apiError));
    } finally {
      setActionKey("");
    }
  }

  async function handleUpload(event) {
    event.preventDefault();

    if (!selectedFile) {
      setActionError({ message: "Choose a file before uploading.", items: [] });
      return;
    }

    setIsUploading(true);
    setActionError(null);
    setSuccess("");

    try {
      await uploadTaskAttachment(numericTaskId, selectedFile);
      setSelectedFile(null);
      setSuccess("Attachment uploaded.");
      await loadTask();
    } catch (apiError) {
      setActionError(parseApiError(apiError));
    } finally {
      setIsUploading(false);
    }
  }

  async function handleDownload(attachment) {
    setActionKey(`download:${attachment.id}`);
    setActionError(null);

    try {
      await downloadTaskAttachment(attachment);
    } catch (apiError) {
      setActionError(parseApiError(apiError));
    } finally {
      setActionKey("");
    }
  }

  async function handleDeleteAttachment(attachmentId) {
    setActionKey(`attachment:${attachmentId}`);
    setActionError(null);
    setSuccess("");

    try {
      await deleteTaskAttachment(attachmentId);
      setConfirmAttachmentId(null);
      setSuccess("Attachment deleted.");
      await loadTask();
    } catch (apiError) {
      setActionError(parseApiError(apiError));
    } finally {
      setActionKey("");
    }
  }

  if (isLoading) {
    return <LoadingScreen message="Loading task..." />;
  }

  if (error && !task) {
    return (
      <section className="space-y-5">
        <Alert title="Could not load task" message={error.message} items={error.items} />
        <Link
          to="/classes"
          className="inline-flex rounded-md bg-blue-600 px-4 py-2.5 text-sm font-semibold text-white transition hover:bg-blue-700 focus:outline-none focus:ring-2 focus:ring-blue-600 focus:ring-offset-2"
        >
          Back to classes
        </Link>
      </section>
    );
  }

  const canManage = task.can_manage;
  const isShared = task.visibility === "shared";
  const isPersonal = task.visibility === "personal";
  const progressStatus = task.my_progress?.status || "pending";
  const isClosed = task.status === "cancelled" || task.status === "archived";

  return (
    <section className="space-y-6">
      <div className="rounded-md border border-slate-200 bg-white p-5 shadow-sm sm:p-6">
        <div className="flex flex-col gap-4 lg:flex-row lg:items-start lg:justify-between">
          <div>
            <p className="text-sm font-semibold uppercase tracking-wide text-blue-600">
              Task detail
            </p>
            <h1 className="mt-2 text-3xl font-bold text-slate-950">
              {task.title}
            </h1>
            <p className="mt-3 max-w-2xl text-base leading-7 text-slate-500">
              {task.description || "No description"}
            </p>
          </div>
          <div className="flex flex-wrap gap-2">
            <StatusBadge value={task.visibility} />
            <StatusBadge value={task.task_type} />
            <StatusBadge value={task.priority} />
            <StatusBadge value={task.status} />
            <StatusBadge value={progressStatus} />
          </div>
        </div>

        <dl className="mt-6 grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
          <div>
            <dt className="text-xs font-semibold uppercase tracking-wide text-slate-500">
              Course
            </dt>
            <dd className="mt-1 text-sm font-medium text-slate-950">
              {task.course ? `${task.course.code} - ${task.course.name}` : "No course"}
            </dd>
          </div>
          <div>
            <dt className="text-xs font-semibold uppercase tracking-wide text-slate-500">
              Deadline
            </dt>
            <dd className="mt-1 text-sm font-medium text-slate-950">
              {formatDeadline(task.deadline)}
            </dd>
          </div>
          <div>
            <dt className="text-xs font-semibold uppercase tracking-wide text-slate-500">
              Creator
            </dt>
            <dd className="mt-1 text-sm font-medium text-slate-950">
              {getCreatorName(task.creator)}
            </dd>
          </div>
          <div>
            <dt className="text-xs font-semibold uppercase tracking-wide text-slate-500">
              Class
            </dt>
            <dd className="mt-1 text-sm font-medium text-slate-950">
              #{task.classroom_id}
            </dd>
          </div>
        </dl>
      </div>

      {actionError ? (
        <Alert
          title="Task action failed"
          message={actionError.message}
          items={actionError.items}
        />
      ) : null}
      {success ? <Alert type="success" title="Updated" message={success} /> : null}

      <div className="rounded-md border border-slate-200 bg-white p-5 shadow-sm sm:p-6">
        <h2 className="text-lg font-semibold text-slate-950">Progress</h2>
        <p className="mt-1 text-sm text-slate-500">
          Mark shared tasks complete for yourself. Personal tasks are completed
          through the personal task editor.
        </p>
        <div className="mt-4 flex flex-wrap gap-2">
          {isShared ? (
            <>
              <button
                type="button"
                disabled={isClosed || actionKey === "progress:completed"}
                onClick={() => handleProgress("completed")}
                className="rounded-md bg-blue-600 px-4 py-2 text-sm font-semibold text-white transition hover:bg-blue-700 focus:outline-none focus:ring-2 focus:ring-blue-600 focus:ring-offset-2 disabled:cursor-not-allowed disabled:bg-blue-300"
              >
                {actionKey === "progress:completed"
                  ? "Saving..."
                  : "Mark complete"}
              </button>
              <button
                type="button"
                disabled={isClosed || actionKey === "progress:pending"}
                onClick={() => handleProgress("pending")}
                className="rounded-md border border-slate-200 px-4 py-2 text-sm font-semibold text-slate-600 transition hover:bg-white focus:outline-none focus:ring-2 focus:ring-blue-600 focus:ring-offset-2 disabled:cursor-not-allowed disabled:opacity-60"
              >
                {actionKey === "progress:pending" ? "Saving..." : "Mark pending"}
              </button>
            </>
          ) : (
            <StatusBadge value={progressStatus} />
          )}
        </div>
      </div>

      {canManage && isShared ? (
        <div className="rounded-md border border-slate-200 bg-white p-5 shadow-sm sm:p-6">
          <h2 className="text-lg font-semibold text-slate-950">
            Representative Controls
          </h2>
          <div className="mt-4 flex flex-wrap gap-2">
            <button
              type="button"
              disabled={actionKey === "status:cancelled"}
              onClick={() => handleStatus("cancelled")}
              className="rounded-md border border-red-200 px-4 py-2 text-sm font-semibold text-red-700 transition hover:bg-red-50 focus:outline-none focus:ring-2 focus:ring-red-600 focus:ring-offset-2 disabled:cursor-not-allowed disabled:opacity-60"
            >
              {actionKey === "status:cancelled" ? "Saving..." : "Cancel task"}
            </button>
            <button
              type="button"
              disabled={actionKey === "status:archived"}
              onClick={() => handleStatus("archived")}
              className="rounded-md border border-slate-200 px-4 py-2 text-sm font-semibold text-slate-600 transition hover:bg-white focus:outline-none focus:ring-2 focus:ring-blue-600 focus:ring-offset-2 disabled:cursor-not-allowed disabled:opacity-60"
            >
              {actionKey === "status:archived" ? "Saving..." : "Archive task"}
            </button>
            {task.status !== "active" ? (
              <button
                type="button"
                disabled={actionKey === "status:active"}
                onClick={() => handleStatus("active")}
                className="rounded-md bg-blue-600 px-4 py-2 text-sm font-semibold text-white transition hover:bg-blue-700 focus:outline-none focus:ring-2 focus:ring-blue-600 focus:ring-offset-2 disabled:cursor-not-allowed disabled:bg-blue-300"
              >
                {actionKey === "status:active" ? "Saving..." : "Reopen task"}
              </button>
            ) : null}
          </div>
        </div>
      ) : null}

      {canManage ? (
        <div className="rounded-md border border-slate-200 bg-white p-5 shadow-sm sm:p-6">
          <h2 className="text-lg font-semibold text-slate-950">
            {isPersonal ? "Personal Task Editor" : "Task Editor"}
          </h2>
          <form className="mt-5 space-y-4" onSubmit={handleSave}>
            <div className="grid gap-4 lg:grid-cols-2">
              <FormField
                id="edit-task-title"
                label="Title"
                name="title"
                onChange={handleEditChange}
                required
                value={editForm.title}
              />
              {isPersonal ? (
                <SelectField
                  id="edit-task-type"
                  label="Task type"
                  name="task_type"
                  onChange={handleEditChange}
                  value={editForm.task_type}
                >
                  {TASK_TYPES.map((type) => (
                    <option key={type} value={type}>
                      {type}
                    </option>
                  ))}
                </SelectField>
              ) : null}
              <SelectField
                id="edit-task-priority"
                label="Priority"
                name="priority"
                onChange={handleEditChange}
                value={editForm.priority}
              >
                {TASK_PRIORITIES.map((priority) => (
                  <option key={priority} value={priority}>
                    {priority}
                  </option>
                ))}
              </SelectField>
              {isPersonal ? (
                <SelectField
                  id="edit-task-status"
                  label="Status"
                  name="status"
                  onChange={handleEditChange}
                  value={editForm.status}
                >
                  <option value="active">active</option>
                  <option value="completed">completed</option>
                  <option value="archived">archived</option>
                </SelectField>
              ) : null}
              <FormField
                id="edit-task-deadline"
                label="Deadline"
                name="deadline"
                onChange={handleEditChange}
                type="datetime-local"
                value={editForm.deadline}
              />
            </div>
            <TextAreaField
              id="edit-task-description"
              label="Description"
              name="description"
              onChange={handleEditChange}
              value={editForm.description}
            />
            <div className="flex flex-col gap-2 sm:flex-row sm:justify-between">
              {isPersonal ? (
                confirmDelete ? (
                  <div className="flex flex-wrap items-center gap-2 rounded-md border border-red-200 bg-red-50 p-2">
                    <span className="text-sm font-medium text-red-700">
                      Delete?
                    </span>
                    <button
                      type="button"
                      disabled={actionKey === "delete-task"}
                      onClick={handleDeleteTask}
                      className="rounded-md bg-red-600 px-3 py-1.5 text-sm font-semibold text-white transition hover:bg-red-700 focus:outline-none focus:ring-2 focus:ring-red-600 focus:ring-offset-2 disabled:cursor-not-allowed disabled:opacity-60"
                    >
                      {actionKey === "delete-task" ? "Deleting..." : "Yes"}
                    </button>
                    <button
                      type="button"
                      disabled={actionKey === "delete-task"}
                      onClick={() => setConfirmDelete(false)}
                      className="rounded-md border border-slate-200 px-3 py-1.5 text-sm font-semibold text-slate-600 transition hover:bg-white focus:outline-none focus:ring-2 focus:ring-blue-600 focus:ring-offset-2"
                    >
                      Cancel
                    </button>
                  </div>
                ) : (
                  <button
                    type="button"
                    onClick={() => setConfirmDelete(true)}
                    className="rounded-md border border-red-200 px-4 py-2 text-sm font-semibold text-red-700 transition hover:bg-red-50 focus:outline-none focus:ring-2 focus:ring-red-600 focus:ring-offset-2"
                  >
                    Delete personal task
                  </button>
                )
              ) : (
                <span />
              )}
              <button
                type="submit"
                disabled={isSaving}
                className="rounded-md bg-blue-600 px-5 py-2.5 text-sm font-semibold text-white transition hover:bg-blue-700 focus:outline-none focus:ring-2 focus:ring-blue-600 focus:ring-offset-2 disabled:cursor-not-allowed disabled:bg-blue-300"
              >
                {isSaving ? "Saving..." : "Save task"}
              </button>
            </div>
          </form>
        </div>
      ) : null}

      <div className="rounded-md border border-slate-200 bg-white p-5 shadow-sm sm:p-6">
        <div className="flex flex-col gap-2 sm:flex-row sm:items-center sm:justify-between">
          <div>
            <h2 className="text-lg font-semibold text-slate-950">
              Attachments
            </h2>
            <p className="mt-1 text-sm text-slate-500">
              Download files attached to this task.
            </p>
          </div>
          <span className="text-sm font-medium text-slate-500">
            {task.attachments.length} files
          </span>
        </div>

        {canManage ? (
          <form
            className="mt-5 flex flex-col gap-3 rounded-md border border-slate-200 bg-slate-50 p-4 sm:flex-row sm:items-end"
            onSubmit={handleUpload}
          >
            <div className="flex-1">
              <label
                htmlFor="task-attachment"
                className="block text-sm font-medium text-slate-600"
              >
                Upload attachment
              </label>
              <input
                className="mt-1 block w-full rounded-md border border-slate-200 bg-white px-3 py-2 text-sm text-slate-950 shadow-sm file:mr-3 file:rounded-md file:border-0 file:bg-blue-50 file:px-3 file:py-1.5 file:text-sm file:font-semibold file:text-blue-700 focus:outline-none focus:ring-2 focus:ring-blue-600 focus:ring-offset-2"
                id="task-attachment"
                onChange={(event) => setSelectedFile(event.target.files?.[0] || null)}
                type="file"
              />
            </div>
            <button
              type="submit"
              disabled={isUploading}
              className="rounded-md bg-blue-600 px-5 py-2.5 text-sm font-semibold text-white transition hover:bg-blue-700 focus:outline-none focus:ring-2 focus:ring-blue-600 focus:ring-offset-2 disabled:cursor-not-allowed disabled:bg-blue-300"
            >
              {isUploading ? "Uploading..." : "Upload"}
            </button>
          </form>
        ) : null}

        {task.attachments.length === 0 ? (
          <p className="mt-5 rounded-md border border-dashed border-slate-200 p-4 text-sm text-slate-500">
            No attachments yet.
          </p>
        ) : (
          <div className="mt-5 space-y-3">
            {task.attachments.map((attachment) => (
              <div
                className="grid gap-3 rounded-md border border-slate-200 p-4 lg:grid-cols-[1fr_auto] lg:items-center"
                key={attachment.id}
              >
                <div>
                  <p className="text-sm font-semibold text-slate-950">
                    {attachment.file_name}
                  </p>
                  <p className="mt-1 text-xs text-slate-500">
                    {attachment.file_type} - {formatFileSize(attachment.file_size)}
                  </p>
                </div>
                <div className="flex flex-wrap gap-2 lg:justify-end">
                  <button
                    type="button"
                    disabled={actionKey === `download:${attachment.id}`}
                    onClick={() => handleDownload(attachment)}
                    className="rounded-md bg-blue-600 px-4 py-2 text-sm font-semibold text-white transition hover:bg-blue-700 focus:outline-none focus:ring-2 focus:ring-blue-600 focus:ring-offset-2 disabled:cursor-not-allowed disabled:bg-blue-300"
                  >
                    {actionKey === `download:${attachment.id}`
                      ? "Downloading..."
                      : "Download"}
                  </button>
                  {canManage ? (
                    confirmAttachmentId === attachment.id ? (
                      <div className="flex flex-wrap items-center gap-2 rounded-md border border-red-200 bg-red-50 p-2">
                        <span className="text-sm font-medium text-red-700">
                          Delete?
                        </span>
                        <button
                          type="button"
                          disabled={actionKey === `attachment:${attachment.id}`}
                          onClick={() => handleDeleteAttachment(attachment.id)}
                          className="rounded-md bg-red-600 px-3 py-1.5 text-sm font-semibold text-white transition hover:bg-red-700 focus:outline-none focus:ring-2 focus:ring-red-600 focus:ring-offset-2 disabled:cursor-not-allowed disabled:opacity-60"
                        >
                          {actionKey === `attachment:${attachment.id}`
                            ? "Deleting..."
                            : "Yes"}
                        </button>
                        <button
                          type="button"
                          disabled={actionKey === `attachment:${attachment.id}`}
                          onClick={() => setConfirmAttachmentId(null)}
                          className="rounded-md border border-slate-200 px-3 py-1.5 text-sm font-semibold text-slate-600 transition hover:bg-white focus:outline-none focus:ring-2 focus:ring-blue-600 focus:ring-offset-2"
                        >
                          Cancel
                        </button>
                      </div>
                    ) : (
                      <button
                        type="button"
                        onClick={() => setConfirmAttachmentId(attachment.id)}
                        className="rounded-md border border-red-200 px-4 py-2 text-sm font-semibold text-red-700 transition hover:bg-red-50 focus:outline-none focus:ring-2 focus:ring-red-600 focus:ring-offset-2"
                      >
                        Delete
                      </button>
                    )
                  ) : null}
                </div>
              </div>
            ))}
          </div>
        )}
      </div>
    </section>
  );
}

export default TaskDetailsPage;

