import { act, fireEvent, render, screen, waitFor, within } from "@testing-library/react";
import { MemoryRouter, Route, Routes } from "react-router-dom";
import { beforeEach, describe, expect, it, vi } from "vitest";

import { listMyClassrooms } from "../api/classrooms.js";
import { listClassCourses } from "../api/courses.js";
import * as api from "../api/resources.js";
import { apiError, classroom, courses, deferred, resource } from "../test/classContentFixtures.js";
import ClassResourcesPage from "./ClassResourcesPage.jsx";

vi.mock("../api/resources.js", () => ({
  listResources: vi.fn(), uploadResource: vi.fn(), updateResource: vi.fn(), deleteResource: vi.fn(),
  downloadResource: vi.fn(), getResource: vi.fn(), reindexResource: vi.fn(),
}));
vi.mock("../api/classrooms.js", () => ({ listMyClassrooms: vi.fn() }));
vi.mock("../api/courses.js", () => ({ listClassCourses: vi.fn() }));

function renderPage() {
  return render(
    <MemoryRouter initialEntries={["/classes/1/resources"]}>
      <Routes><Route path="/classes/:classId/resources" element={<ClassResourcesPage />} /></Routes>
    </MemoryRouter>,
  );
}

function selectFile(file) {
  fireEvent.change(screen.getByLabelText(/PDF file/), { target: { files: [file] } });
}

describe("class resources", () => {
  beforeEach(() => {
    vi.resetAllMocks();
    listMyClassrooms.mockResolvedValue([classroom]);
    listClassCourses.mockResolvedValue(courses);
    api.listResources.mockResolvedValue([resource]);
    api.getResource.mockResolvedValue(resource);
  });

  it("renders loading and an empty state", async () => {
    api.listResources.mockResolvedValue([]);
    renderPage();
    expect(screen.getByText("Loading resources...")).toBeInTheDocument();
    expect(await screen.findByText("No resources yet")).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Upload resource" })).toBeInTheDocument();
  });

  it.each([
    ["pending", "Waiting to index"], ["processing", "Indexing"], ["indexed", "Ready"], ["failed", "Indexing failed"],
  ])("shows %s indexing status, metadata, and correct reindex availability", async (status, label) => {
    api.listResources.mockResolvedValue([{ ...resource, indexing_status: status, indexing_error: "PDF extraction failed." }]);
    renderPage();
    expect(await screen.findByText(resource.title)).toBeInTheDocument();
    expect(screen.getAllByText(label).length).toBeGreaterThan(0);
    expect(screen.getByText(/notes.pdf · 2.0 KB/)).toBeInTheDocument();
    expect(screen.getByText("CS201 - Data Structures")).toBeInTheDocument();
    expect(screen.getByText("Enabled")).toBeInTheDocument();
    const retry = screen.getByRole("button", { name: "Reindex resource" });
    if (status === "processing") expect(retry).toBeDisabled();
    else expect(retry).toBeEnabled();
    expect(screen.getByRole("button", { name: "Download PDF" })).toBeEnabled();
    if (status === "failed") {
      expect(screen.getByRole("alert")).toHaveTextContent("PDF extraction failed.");
      expect(screen.getByText(/remains downloadable while enabled/)).toBeInTheDocument();
    }
  });

  it("uses can_manage for controls and allows student downloads", async () => {
    api.listResources.mockResolvedValue([{ ...resource, can_manage: false }]);
    renderPage();
    fireEvent.click(await screen.findByRole("button", { name: "Download PDF" }));
    await waitFor(() => expect(api.downloadResource).toHaveBeenCalledWith(expect.objectContaining({ id: 20 })));
    for (const name of ["Upload resource", "Edit resource", "Disable resource", "Reindex resource", "Delete resource"]) {
      expect(screen.queryByRole("button", { name })).not.toBeInTheDocument();
    }
  });

  it("uploads PDF metadata with progress, preserves failures, and prevents duplicate submissions", async () => {
    const upload = deferred();
    api.uploadResource.mockReturnValueOnce(upload.promise).mockResolvedValueOnce(resource);
    renderPage();
    fireEvent.click(await screen.findByRole("button", { name: "Upload resource" }));
    fireEvent.change(screen.getByLabelText(/Title/), { target: { value: "Lecture notes" } });
    fireEvent.change(screen.getByLabelText("Description"), { target: { value: "Read chapter 1." } });
    fireEvent.change(screen.getByLabelText("Scope"), { target: { value: "11" } });
    expect(screen.queryByRole("option", { name: /CS101/ })).not.toBeInTheDocument();
    expect(screen.getByText(/Maximum 10 MB/)).toBeInTheDocument();
    selectFile(new File(["text"], "notes.txt", { type: "text/plain" }));
    expect(screen.getByRole("alert")).toHaveTextContent("Select a PDF");
    fireEvent.submit(screen.getByLabelText(/Title/).closest("form"));
    expect(api.uploadResource).not.toHaveBeenCalled();
    selectFile(new File(["text"], "notes.pdf", { type: "text/plain" }));
    expect(screen.getByRole("alert")).toHaveTextContent("PDF file type");
    const file = new File(["%PDF-1.7"], "notes.PDF", { type: "application/pdf" });
    selectFile(file);
    const form = screen.getByLabelText(/Title/).closest("form");
    fireEvent.submit(form);
    fireEvent.submit(form);
    expect(api.uploadResource).toHaveBeenCalledTimes(1);
    expect(api.uploadResource).toHaveBeenCalledWith(1, {
      title: "Lecture notes", description: "Read chapter 1.", class_course_id: 11, file,
    }, expect.any(Function));
    act(() => api.uploadResource.mock.calls[0][2]({ loaded: 5, total: 10 }));
    expect(screen.getByRole("progressbar")).toHaveAttribute("value", "50");
    act(() => api.uploadResource.mock.calls[0][2]({ loaded: 10, total: 10 }));
    expect(screen.getByRole("status")).toHaveTextContent("Preparing resource");
    await act(async () => upload.reject(apiError(413)));
    expect(screen.getByRole("alert")).toHaveTextContent("PDF is too large");
    expect(screen.getByLabelText(/Title/)).toHaveValue("Lecture notes");
    expect(screen.getByLabelText("Scope")).toHaveValue("11");
    expect(screen.getByLabelText(/PDF file/).files[0]).toBe(file);
    // fireEvent's synthetic FileList does not set the native file input value.
    fireEvent.submit(form);
    await waitFor(() => expect(screen.queryByRole("dialog")).not.toBeInTheDocument());
    expect(api.uploadResource).toHaveBeenCalledTimes(2);
    expect(api.getResource).toHaveBeenCalledWith(20);
  });

  it("edits metadata without exposing mutable scope or PDF fields", async () => {
    const updated = { ...resource, title: "Updated notes", description: null };
    api.updateResource.mockResolvedValue(updated);
    api.getResource.mockResolvedValue(updated);
    renderPage();
    fireEvent.click(await screen.findByRole("button", { name: "Edit resource" }));
    const dialog = screen.getByRole("dialog");
    expect(within(dialog).queryByRole("combobox")).not.toBeInTheDocument();
    expect(dialog.querySelector('input[type="file"]')).toBeNull();
    expect(within(dialog).getByText(/scope and PDF cannot be changed/)).toBeInTheDocument();
    fireEvent.change(screen.getByLabelText(/Title/), { target: { value: "Updated notes" } });
    fireEvent.change(screen.getByLabelText("Description"), { target: { value: "" } });
    fireEvent.click(screen.getByRole("button", { name: "Save changes" }));
    expect(await screen.findByText("Updated notes")).toBeInTheDocument();
    expect(api.updateResource).toHaveBeenCalledWith(20, { title: "Updated notes", description: null });
    expect(api.getResource).toHaveBeenCalledWith(20);
  });

  it("reindexes a failed resource and refreshes the affected metadata", async () => {
    api.listResources.mockResolvedValue([{ ...resource, indexing_status: "failed", indexing_error: "Try again later." }]);
    const request = deferred();
    api.reindexResource.mockReturnValue(request.promise);
    renderPage();
    fireEvent.click(await screen.findByRole("button", { name: "Reindex resource" }));
    expect(screen.getByRole("button", { name: "Reindex resource" })).toBeDisabled();
    await act(async () => request.resolve(resource));
    expect(await screen.findByText("Ready")).toBeInTheDocument();
    expect(screen.queryByText("Try again later.")).not.toBeInTheDocument();
    expect(api.reindexResource).toHaveBeenCalledWith(20);
    expect(api.getResource).toHaveBeenCalledWith(20);
  });

  it("disables and re-enables a resource using PATCH metadata while blocking downloads and indexing", async () => {
    const disabled = { ...resource, is_enabled: false, indexing_status: "pending" };
    api.updateResource.mockResolvedValueOnce(disabled).mockResolvedValueOnce(resource);
    renderPage();
    fireEvent.click(await screen.findByRole("button", { name: "Disable resource" }));
    const enable = await screen.findByRole("button", { name: "Enable resource" });
    await waitFor(() => expect(enable).toBeEnabled());
    expect(screen.getByText("Disabled")).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Download PDF" })).toBeDisabled();
    expect(screen.getByRole("button", { name: "Reindex resource" })).toBeDisabled();
    expect(api.getResource).not.toHaveBeenCalled();
    expect(api.updateResource).toHaveBeenLastCalledWith(20, { is_enabled: false });
    fireEvent.click(enable);
    await waitFor(() => expect(screen.getByRole("button", { name: "Download PDF" })).toBeEnabled());
    expect(api.updateResource).toHaveBeenLastCalledWith(20, { is_enabled: true });
    expect(api.getResource).toHaveBeenCalledWith(20);
  });

  it("shows conflict errors from reindexing", async () => {
    api.reindexResource.mockRejectedValue(apiError(409, "Enable the resource before indexing"));
    renderPage();
    fireEvent.click(await screen.findByRole("button", { name: "Reindex resource" }));
    expect(await screen.findByRole("alert")).toHaveTextContent("Enable the resource before indexing");
  });

  it("keeps a resource until deletion succeeds and preserves the confirmation after errors", async () => {
    api.deleteResource.mockRejectedValueOnce(apiError(403)).mockResolvedValueOnce();
    renderPage();
    fireEvent.click(await screen.findByRole("button", { name: "Delete resource" }));
    expect(api.deleteResource).not.toHaveBeenCalled();
    fireEvent.click(within(screen.getByRole("dialog")).getByRole("button", { name: "Delete resource" }));
    expect(await screen.findByRole("alert")).toHaveTextContent("You cannot perform this action");
    expect(screen.getByRole("article")).toBeInTheDocument();
    fireEvent.click(within(screen.getByRole("dialog")).getByRole("button", { name: "Delete resource" }));
    expect(await screen.findByText("No resources yet")).toBeInTheDocument();
    expect(api.deleteResource).toHaveBeenCalledWith(20);
  });

  it.each([403, 404, 500, 503])("handles a %s list error without exposing internal detail", async (status) => {
    api.listResources.mockRejectedValue(apiError(status, "Secret resource exists"));
    renderPage();
    expect(await screen.findByRole("alert")).not.toHaveTextContent("Secret resource exists");
    expect(screen.queryByRole("article")).not.toBeInTheDocument();
    expect(screen.queryByRole("button", { name: "Upload resource" })).not.toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Try again" })).toBeInTheDocument();
  });

  it("handles an exact-ID download 404 generically", async () => {
    api.downloadResource.mockRejectedValue(apiError(404, "Resource exists in another class"));
    renderPage();
    fireEvent.click(await screen.findByRole("button", { name: "Download PDF" }));
    expect(await screen.findByRole("alert")).toHaveTextContent("This content is unavailable or could not be found");
    expect(screen.queryByText("Resource exists in another class")).not.toBeInTheDocument();
  });

  it("does not retry an already-saved upload when the metadata refresh fails", async () => {
    api.uploadResource.mockResolvedValue(resource);
    api.getResource.mockRejectedValue(apiError(503, "Internal provider credentials"));
    renderPage();
    fireEvent.click(await screen.findByRole("button", { name: "Upload resource" }));
    fireEvent.change(screen.getByLabelText(/Title/), { target: { value: "Notes" } });
    selectFile(new File(["%PDF-1.7"], "notes.pdf", { type: "application/pdf" }));
    fireEvent.submit(screen.getByLabelText(/Title/).closest("form"));
    await waitFor(() => expect(screen.queryByRole("dialog")).not.toBeInTheDocument());
    expect(await screen.findByText("ClassFlow is temporarily unavailable. Please try again.")).toBeInTheDocument();
    expect(screen.getByRole("article")).toBeInTheDocument();
    expect(api.uploadResource).toHaveBeenCalledTimes(1);
    expect(screen.queryByText("Internal provider credentials")).not.toBeInTheDocument();
  });

  it("does not show upload controls for an empty student collection", async () => {
    listMyClassrooms.mockResolvedValue([{ ...classroom, membership: { role: "student", status: "approved" } }]);
    api.listResources.mockResolvedValue([]);
    renderPage();
    expect(await screen.findByText("No resources yet")).toBeInTheDocument();
    expect(screen.queryByRole("button", { name: "Upload resource" })).not.toBeInTheDocument();
  });
});
