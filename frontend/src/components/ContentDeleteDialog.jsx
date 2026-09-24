import Alert from "./Alert.jsx";
import Button from "./Button.jsx";
import Modal from "./Modal.jsx";

function ContentDeleteDialog({ kind, item, busy, error, onClose, onConfirm }) {
  return (
    <Modal isOpen={Boolean(item)} onClose={onClose} isBusy={busy} title={`Delete ${kind}?`}>
      <div className="space-y-4">
        <p className="break-words text-sm text-slate-600">
          Delete “{item?.title}”? This cannot be undone.
        </p>
        {error ? <Alert title="Deletion failed" {...error} /> : null}
        <div className="flex flex-col-reverse gap-2 sm:flex-row sm:justify-end">
          <Button disabled={busy} onClick={onClose}>Cancel</Button>
          <Button disabled={busy} onClick={onConfirm} variant="danger">
            {busy ? "Deleting..." : `Delete ${kind}`}
          </Button>
        </div>
      </div>
    </Modal>
  );
}

export default ContentDeleteDialog;
