import { useEffect, useRef } from "react";

import Button from "./Button.jsx";

function Modal({ children, isOpen, onClose, title, description }) {
  const onCloseRef = useRef(onClose);
  const panelRef = useRef(null);

  useEffect(() => {
    onCloseRef.current = onClose;
  }, [onClose]);

  useEffect(() => {
    if (!isOpen) return undefined;

    const previousActiveElement = document.activeElement;
    panelRef.current?.focus();

    function handleKeyDown(event) {
      if (event.key === "Escape") {
        onCloseRef.current();
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
      className="fixed inset-0 z-50 flex items-end bg-slate-950/40 p-3 sm:items-center sm:justify-center"
      role="dialog"
    >
      <button
        aria-label="Close dialog"
        className="absolute inset-0 z-0 cursor-default"
        onClick={() => onCloseRef.current()}
        type="button"
      />
      <div
        className="relative z-10 max-h-[calc(100vh-2rem)] w-full overflow-y-auto rounded-xl bg-white p-5 shadow-xl outline-none sm:max-w-2xl sm:p-6"
        ref={panelRef}
        tabIndex={-1}
      >
        <div className="flex items-start justify-between gap-4">
          <div>
            <h2 className="text-lg font-semibold text-slate-900">{title}</h2>
            {description ? (
              <p className="mt-1 text-sm leading-6 text-slate-500">
                {description}
              </p>
            ) : null}
          </div>
          <Button aria-label="Close dialog" onClick={onClose} variant="subtle">
            Close
          </Button>
        </div>
        <div className="mt-5">{children}</div>
      </div>
    </div>
  );
}

export default Modal;
