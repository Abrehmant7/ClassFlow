import { useEffect, useRef, useState } from "react";
import { Link, useParams, useSearchParams } from "react-router-dom";

import { deleteResource, downloadResource, getResource, listResources, reindexResource, updateResource, uploadResource } from "../api/resources.js";
import Alert from "../components/Alert.jsx";
import Button from "../components/Button.jsx";
import ClassWorkspaceHeader from "../components/ClassWorkspaceHeader.jsx";
import ContentDates from "../components/ContentDates.jsx";
import ContentDeleteDialog from "../components/ContentDeleteDialog.jsx";
import EmptyState from "../components/EmptyState.jsx";
import LoadingScreen from "../components/LoadingScreen.jsx";
import ResourceForm from "../components/ResourceForm.jsx";
import StatusBadge from "../components/StatusBadge.jsx";
import useClassContent from "../hooks/useClassContent.js";
import useContentAction from "../hooks/useContentAction.js";
import { contentScope, INDEXING_LABELS, parseContentError } from "../utils/classContent.js";
import { formatFileSize } from "../utils/tasks.js";

function ResourcesWorkspace({ classId, resourceId }) {
  const content = useClassContent(classId, listResources);
  const action = useContentAction();
  const [editor, setEditor] = useState(null);
  const [deleteTarget, setDeleteTarget] = useState(null);
  const [success, setSuccess] = useState("");
  const headingRef = useRef(null);

  useEffect(() => {
    if (!content.isLoading && resourceId && content.items.some((item) => item.id === Number(resourceId))) {
      document.getElementById(`resource-${resourceId}`)?.focus();
    }
  }, [content.isLoading, content.items, resourceId]);

  async function refreshResource(resource) {
    // Disabled rows are excluded from GET, even for representatives. PATCH's
    // complete response is the only available refreshed metadata in that case.
    if (!resource.is_enabled) return;
    try {
      content.upsert(await getResource(resource.id));
    } catch (error) {
      if (error.response?.status === 404) content.remove(resource.id);
      action.setError(parseContentError(error));
    }
  }

  async function save(payload, onProgress) {
    const saved = editor.item
      ? await updateResource(editor.item.id, payload)
      : await uploadResource(classId, payload, onProgress);
    content.upsert(saved);
    setEditor(null);
    setSuccess("Resource saved.");
    await refreshResource(saved);
  }

  function manage(operation) {
    setSuccess("");
    action.run(async () => {
      const saved = await operation();
      content.upsert(saved);
      setSuccess(saved.is_enabled ? "Resource updated." : "Resource disabled. You can re-enable it here before reloading the page.");
      await refreshResource(saved);
    });
  }

  function download(resource) {
    setSuccess("");
    action.run(() => downloadResource(resource));
  }

  function confirmDelete() {
    action.run(async () => {
      await deleteResource(deleteTarget.id);
      content.remove(deleteTarget.id);
      setDeleteTarget(null);
      setSuccess("Resource deleted.");
      window.setTimeout(() => headingRef.current?.focus(), 0);
    });
  }

  function openEditor(item = null) {
    action.setError(null);
    setSuccess("");
    setEditor({ item });
  }

  if (content.isLoading) return <LoadingScreen message="Loading resources..." />;

  return (
    <section className="min-w-0 space-y-6">
      <ClassWorkspaceHeader classroom={content.classroom} membership={content.classroom?.membership} />
      <div className="flex flex-wrap items-center justify-between gap-3">
        <h2 className="text-xl font-semibold text-slate-900 outline-none" ref={headingRef} tabIndex={-1}>Resources</h2>
        <div className="flex flex-wrap gap-2">
          <Button disabled={action.busy} onClick={content.load}>Refresh resources</Button>
          {content.canCreate ? <Button disabled={action.busy} onClick={() => openEditor()} variant="primary">Upload resource</Button> : null}
        </div>
      </div>
      {content.error ? (
        <div className="space-y-3">
          <Alert title="Could not load resources" {...content.error} />
          <Button onClick={content.load}>Try again</Button>
          <Link className="ml-3 text-sm font-semibold text-blue-700 cf-focus" to="/classes">Back to classes</Link>
        </div>
      ) : null}
      {action.error && !deleteTarget ? <Alert title="Resource action failed" {...action.error} /> : null}
      {success ? <Alert type="success" title="Updated" message={success} /> : null}
      {!content.error && content.items.length === 0 ? <EmptyState title="No resources yet" message="Class PDFs will appear here when they are uploaded." /> : null}
      <div className="space-y-4">
        {content.items.map((resource) => (
          <article aria-labelledby={`resource-${resource.id}`} className="cf-card min-w-0 space-y-4 p-4 outline-none focus-visible:ring-2 focus-visible:ring-blue-600 sm:p-5" id={`resource-${resource.id}`} key={resource.id} tabIndex={-1}>
            <div className="flex flex-wrap items-center gap-2">
              <StatusBadge value={resource.is_enabled ? "active" : "inactive"} label={resource.is_enabled ? "Enabled" : "Disabled"} />
              <StatusBadge value={resource.indexing_status} label={INDEXING_LABELS[resource.indexing_status] || "Unknown indexing state"} />
              <span className="min-w-0 break-words text-xs font-semibold text-cyan-700">{contentScope(resource.class_course_id, content.courses)}</span>
            </div>
            <h3 className="break-words text-lg font-semibold text-slate-900" id={`resource-${resource.id}`}>{resource.title}</h3>
            {resource.description ? <p className="whitespace-pre-wrap break-words text-sm leading-7 text-slate-700">{resource.description}</p> : null}
            <p className="break-words text-sm text-slate-500">{resource.file_name} · {formatFileSize(resource.file_size) || "Size unavailable"}</p>
            <ContentDates createdAt={resource.created_at} updatedAt={resource.updated_at} />
            {resource.indexing_status === "failed" ? (
              <div className="break-words">
                <Alert type="warning" title="Indexing failed"
                  message={resource.indexing_error || "This PDF could not be indexed."} />
                <p className="mt-2 text-sm text-slate-600">Indexing failure does not remove the PDF. It remains downloadable while enabled.</p>
              </div>
            ) : null}
            {!resource.is_enabled ? <p className="text-sm text-slate-600">Enable this resource to download or reindex it. Disabled resources disappear after reloading this page.</p> : null}
            <div className="flex flex-wrap gap-2 border-t border-slate-100 pt-4">
              <Button disabled={action.busy || !resource.is_enabled} onClick={() => download(resource)}>Download PDF</Button>
              {resource.is_enabled ? <Button disabled={action.busy} onClick={() => action.run(() => refreshResource(resource))}>Refresh status</Button> : null}
              {resource.can_manage === true ? (
                <>
                  <Button disabled={action.busy} onClick={() => openEditor(resource)}>Edit resource</Button>
                  <Button disabled={action.busy} onClick={() => manage(() => updateResource(resource.id, { is_enabled: !resource.is_enabled }))}>
                    {resource.is_enabled ? "Disable resource" : "Enable resource"}
                  </Button>
                  <Button disabled={action.busy || !resource.is_enabled || resource.indexing_status === "processing"}
                    onClick={() => manage(() => reindexResource(resource.id))}>Reindex resource</Button>
                  <Button disabled={action.busy} onClick={() => { action.setError(null); setSuccess(""); setDeleteTarget(resource); }} variant="danger">Delete resource</Button>
                </>
              ) : null}
            </div>
          </article>
        ))}
      </div>
      {editor ? <ResourceForm resource={editor.item} courses={content.courses} onClose={() => setEditor(null)} onSave={save} /> : null}
      <ContentDeleteDialog kind="resource" item={deleteTarget} busy={action.busy} error={action.error}
        onClose={() => { setDeleteTarget(null); action.setError(null); }} onConfirm={confirmDelete} />
    </section>
  );
}

export default function ClassResourcesPage() {
  const { classId } = useParams();
  const [searchParams] = useSearchParams();
  return <ResourcesWorkspace classId={Number(classId)} key={classId} resourceId={searchParams.get("resource")} />;
}
