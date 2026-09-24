import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { useState } from "react";
import { describe, expect, it } from "vitest";

import Modal from "./Modal.jsx";

function Example({ busy = false }) {
  const [open, setOpen] = useState(false);
  return (
    <>
      <button onClick={() => setOpen(true)}>Open form</button>
      <Modal isOpen={open} isBusy={busy} onClose={() => setOpen(false)} title="Example form" description="Form instructions">
        <label htmlFor="test-title">Title</label><input id="test-title" />
        <button>Save</button>
      </Modal>
    </>
  );
}

describe("Modal keyboard accessibility", () => {
  it("names the dialog, traps tab focus and restores the trigger on Escape", async () => {
    render(<Example />);
    const trigger = screen.getByRole("button", { name: "Open form" });
    trigger.focus();
    fireEvent.click(trigger);
    const dialog = screen.getByRole("dialog", { name: "Example form" });
    expect(dialog).toHaveAccessibleDescription("Form instructions");
    const first = screen.getByRole("button", { name: "Close dialog" });
    const last = screen.getByRole("button", { name: "Save" });
    fireEvent.keyDown(document.activeElement, { key: "Tab" });
    expect(first).toHaveFocus();
    fireEvent.keyDown(first, { key: "Tab", shiftKey: true });
    expect(last).toHaveFocus();
    fireEvent.keyDown(last, { key: "Tab" });
    expect(first).toHaveFocus();
    fireEvent.keyDown(first, { key: "Escape" });
    await waitFor(() => expect(screen.queryByRole("dialog")).not.toBeInTheDocument());
    expect(trigger).toHaveFocus();
  });

  it("does not close during submission", () => {
    render(<Example busy />);
    fireEvent.click(screen.getByRole("button", { name: "Open form" }));
    fireEvent.keyDown(document.activeElement, { key: "Escape" });
    expect(screen.getByRole("dialog")).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Close dialog" })).toBeDisabled();
  });
});
