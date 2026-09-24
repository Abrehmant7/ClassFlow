import { useEffect, useId, useRef } from "react";

import Button from "./Button.jsx";

function Modal({ children, isOpen, onClose, title, description, isBusy = false }) {
  const titleId = useId();
  const descriptionId = useId();
  const onCloseRef = useRef(onClose);
  const busyRef = useRef(isBusy);
  const panelRef = useRef(null);

  useEffect(() => {
    onCloseRef.current = onClose;
    busyRef.current = isBusy;
  }, [onClose, isBusy]);

  useEffect(() => {
    if (!isOpen) return undefined;

    const previousActiveElement = document.activeElement;
    panelRef.current?.focus();

    function handleKeyDown(event) {
      if (event.key === "Escape") {
        event.preventDefault();
        if (!busyRef.current) onCloseRef.current();
      }
      if (event.key === "Tab") {
        const focusable = [...(panelRef.current?.querySelectorAll(
          'button, [href], input, select, textarea, [tabindex]:not([tabindex="-1"])',
        ) || [])].filter((element) => !element.matches(':disabled, [hidden], [aria-hidden="true"]'));
        const first = focusable[0];
        const last = focusable[focusable.length - 1];
        if (!first) {
          event.preventDefault();
          panelRef.current?.focus();
        } else if (event.shiftKey && (document.activeElement === first || !focusable.includes(document.activeElement))) {
          event.preventDefault();
          last.focus();
        } else if (!event.shiftKey && (document.activeElement === last || !focusable.includes(document.activeElement))) {
          event.preventDefault();
          first.focus();
        }
      }
    }

    document.addEventListener("keydown", handleKeyDown);
    return () => {
      document.removeEventListener("keydown", handleKeyDown);
      previousActiveElement?.focus?.();
    };
  }, [isOpen]);

  if (!isOpen) return null;

  return (
    <div
      aria-modal="true"
      aria-labelledby={titleId}
      aria-describedby={description ? descriptionId : undefined}
      aria-busy={isBusy}
      className="fixed inset-0 z-50 flex items-end bg-slate-950/40 p-3 sm:items-center sm:justify-center"
      role="dialog"
    >
      <button
        aria-hidden="true"
        className="absolute inset-0 z-0 cursor-default"
        disabled={isBusy}
        tabIndex={-1}
        onClick={() => { if (!busyRef.current) onCloseRef.current(); }}
        type="button"
      />
      <div
        className="relative z-10 max-h-[calc(100vh-2rem)] w-full overflow-y-auto rounded-xl bg-white p-5 shadow-xl outline-none sm:max-w-2xl sm:p-6"
        ref={panelRef}
        tabIndex={-1}
      >
        <div className="flex items-start justify-between gap-4">
          <div>
            <h2 id={titleId} className="text-lg font-semibold text-slate-900">{title}</h2>
            {description ? (
              <p id={descriptionId} className="mt-1 text-sm leading-6 text-slate-500">
                {description}
              </p>
            ) : null}
          </div>
          <Button aria-label="Close dialog" disabled={isBusy} onClick={onClose} variant="subtle">
            Close
          </Button>
        </div>
        <div className="mt-5">{children}</div>
      </div>
    </div>
  );
}

export default Modal;
