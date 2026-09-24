import { useRef, useState } from "react";
import { Link, useParams } from "react-router-dom";

import { createAnnouncement, deleteAnnouncement, listAnnouncements, updateAnnouncement } from "../api/announcements.js";
import Alert from "../components/Alert.jsx";
import AnnouncementForm from "../components/AnnouncementForm.jsx";
import Button from "../components/Button.jsx";
import ClassWorkspaceHeader from "../components/ClassWorkspaceHeader.jsx";
import ContentDates from "../components/ContentDates.jsx";
import ContentDeleteDialog from "../components/ContentDeleteDialog.jsx";
import EmptyState from "../components/EmptyState.jsx";
import LoadingScreen from "../components/LoadingScreen.jsx";
import StatusBadge from "../components/StatusBadge.jsx";
import useClassContent from "../hooks/useClassContent.js";
import useContentAction from "../hooks/useContentAction.js";
import { contentScope, parseContentError } from "../utils/classContent.js";

function AnnouncementsWorkspace({ classId }) {
  const content = useClassContent(classId, listAnnouncements);
  const action = useContentAction();
  const [editor, setEditor] = useState(null);
  const [deleteTarget, setDeleteTarget] = useState(null);
  const [success, setSuccess] = useState("");
  const headingRef = useRef(null);

  async function refreshOrder() {
    try {
      content.setItems(await listAnnouncements(classId));
    } catch (error) {
      if ([403, 404].includes(error.response?.status)) {
        content.setItems([]);
        content.setError(parseContentError(error));
      }
      action.setError(parseContentError(error));
    }
  }

  async function save(payload) {
    const saved = editor.item
      ? await updateAnnouncement(editor.item.id, payload)
      : await createAnnouncement(classId, payload);
    content.upsert(saved);
    setEditor(null);
    setSuccess("Announcement saved.");
    await refreshOrder();
  }

  function pin(item) {
    setSuccess("");
    action.run(async () => {
      const saved = await updateAnnouncement(item.id, { is_pinned: !item.is_pinned });
      content.upsert(saved);
      setSuccess(saved.is_pinned ? "Announcement pinned." : "Announcement unpinned.");
      await refreshOrder();
    });
  }

  function confirmDelete() {
    action.run(async () => {
      await deleteAnnouncement(deleteTarget.id);
      content.remove(deleteTarget.id);
      setDeleteTarget(null);
      setSuccess("Announcement deleted.");
      // The original trigger was removed with its card.
      window.setTimeout(() => headingRef.current?.focus(), 0);
    });
  }

  function openEditor(item = null) {
    action.setError(null);
    setSuccess("");
    setEditor({ item });
  }

  if (content.isLoading) return <LoadingScreen message="Loading announcements..." />;

  // Stable partition: preserve the backend's order within both groups.
  const announcements = [
    ...content.items.filter((item) => item.is_pinned),
    ...content.items.filter((item) => !item.is_pinned),
  ];

  return (
    <section className="min-w-0 space-y-6">
      <ClassWorkspaceHeader classroom={content.classroom} membership={content.classroom?.membership} />
      <div className="flex flex-wrap items-center justify-between gap-3">
        <h2 className="text-xl font-semibold text-slate-900 outline-none" ref={headingRef} tabIndex={-1}>Announcements</h2>
        <div className="flex flex-wrap gap-2">
          <Button disabled={action.busy} onClick={content.load}>Refresh announcements</Button>
          {content.canCreate ? <Button disabled={action.busy} onClick={() => openEditor()} variant="primary">New announcement</Button> : null}
        </div>
      </div>
      {content.error ? (
        <div className="space-y-3">
          <Alert title="Could not load announcements" {...content.error} />
          <Button onClick={content.load}>Try again</Button>
          <Link className="ml-3 text-sm font-semibold text-blue-700 cf-focus" to="/classes">Back to classes</Link>
        </div>
      ) : null}
      {action.error && !deleteTarget ? <Alert title="Announcement action failed" {...action.error} /> : null}
      {success ? <Alert type="success" title="Updated" message={success} /> : null}
      {!content.error && announcements.length === 0 ? <EmptyState title="No announcements yet" message="Class announcements will appear here when they are posted." /> : null}
      <div className="space-y-4">
        {announcements.map((item) => (
          <article aria-labelledby={`announcement-${item.id}`} className="cf-card min-w-0 space-y-4 p-4 sm:p-5" key={item.id}>
            <div className="flex flex-wrap items-center gap-2">
              {item.is_pinned ? <StatusBadge value="pinned" label="Pinned" /> : null}
              <span className="min-w-0 break-words text-xs font-semibold text-cyan-700">{contentScope(item.class_course_id, content.courses)}</span>
            </div>
            <h3 className="break-words text-lg font-semibold text-slate-900" id={`announcement-${item.id}`}>{item.title}</h3>
            <p className="whitespace-pre-wrap break-words text-sm leading-7 text-slate-700">{item.body}</p>
            <ContentDates createdAt={item.created_at} updatedAt={item.updated_at} />
            {item.can_manage === true ? (
              <div className="flex flex-wrap gap-2 border-t border-slate-100 pt-4">
                <Button disabled={action.busy} onClick={() => openEditor(item)}>Edit announcement</Button>
                <Button disabled={action.busy} onClick={() => pin(item)}>{item.is_pinned ? "Unpin announcement" : "Pin announcement"}</Button>
                <Button disabled={action.busy} onClick={() => { action.setError(null); setSuccess(""); setDeleteTarget(item); }} variant="danger">Delete announcement</Button>
              </div>
            ) : null}
          </article>
        ))}
      </div>
      {editor ? <AnnouncementForm announcement={editor.item} courses={content.courses} onClose={() => setEditor(null)} onSave={save} /> : null}
      <ContentDeleteDialog kind="announcement" item={deleteTarget} busy={action.busy} error={action.error}
        onClose={() => { setDeleteTarget(null); action.setError(null); }} onConfirm={confirmDelete} />
    </section>
  );
}

export default function ClassAnnouncementsPage() {
  const { classId } = useParams();
  return <AnnouncementsWorkspace classId={Number(classId)} key={classId} />;
}
