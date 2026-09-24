import { act, fireEvent, render, screen, waitFor, within } from "@testing-library/react";
import { Link, MemoryRouter, Route, Routes } from "react-router-dom";
import { beforeEach, describe, expect, it, vi } from "vitest";

import * as api from "../api/announcements.js";
import { listMyClassrooms } from "../api/classrooms.js";
import { listClassCourses } from "../api/courses.js";
import { announcement, apiError, classroom, courses, deferred } from "../test/classContentFixtures.js";
import ClassAnnouncementsPage from "./ClassAnnouncementsPage.jsx";

vi.mock("../api/announcements.js", () => ({
  listAnnouncements: vi.fn(), createAnnouncement: vi.fn(), updateAnnouncement: vi.fn(), deleteAnnouncement: vi.fn(),
}));
vi.mock("../api/classrooms.js", () => ({ listMyClassrooms: vi.fn() }));
vi.mock("../api/courses.js", () => ({ listClassCourses: vi.fn() }));

function renderPage() {
  return render(
    <MemoryRouter initialEntries={["/classes/1/announcements"]}>
      <Link to="/classes/2/announcements">Other classroom</Link>
      <Routes><Route path="/classes/:classId/announcements" element={<ClassAnnouncementsPage />} /></Routes>
    </MemoryRouter>,
  );
}

function fillForm(title = "Exam update", body = "Bring a calculator.") {
  fireEvent.change(screen.getByLabelText(/Title/), { target: { value: title } });
  fireEvent.change(screen.getByLabelText(/Body/), { target: { value: body } });
}

describe("class announcements", () => {
  beforeEach(() => {
    vi.resetAllMocks();
    listMyClassrooms.mockResolvedValue([classroom]);
    listClassCourses.mockResolvedValue(courses);
    api.listAnnouncements.mockResolvedValue([announcement]);
  });

  it("shows loading, an empty state, and classroom navigation", async () => {
    const request = deferred();
    api.listAnnouncements.mockReturnValueOnce(request.promise);
    renderPage();
    expect(screen.getByText("Loading announcements...")).toBeInTheDocument();
    await act(async () => request.resolve([]));
    expect(await screen.findByText("No announcements yet")).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "New announcement" })).toBeInTheDocument();
    expect(screen.getByRole("link", { name: "Resources" })).toHaveAttribute("href", "/classes/1/resources");
  });

  it("partitions pinned announcements stably and resolves course names and dates", async () => {
    api.listAnnouncements.mockResolvedValue([
      announcement,
      { ...announcement, id: 11, title: "First pin", is_pinned: true, class_course_id: 11 },
      { ...announcement, id: 12, title: "Second pin", is_pinned: true, updated_at: "2026-09-21T10:00:00Z" },
      { ...announcement, id: 13, title: "Second normal" },
    ]);
    renderPage();
    const articles = await screen.findAllByRole("article");
    expect(articles.map((article) => within(article).getByRole("heading").textContent))
      .toEqual(["First pin", "Second pin", "Class meeting", "Second normal"]);
    expect(within(articles[0]).getByText("CS201 - Data Structures")).toBeInTheDocument();
    expect(within(articles[0]).getByText("Pinned")).toBeInTheDocument();
    expect(articles[1].querySelectorAll("time")).toHaveLength(2);
    expect(articles[2].querySelectorAll("time")).toHaveLength(1);
    expect(within(articles[2]).getByText("Entire class")).toBeInTheDocument();
  });

  it("uses per-item can_manage flags even when membership says representative", async () => {
    api.listAnnouncements.mockResolvedValue([{ ...announcement, can_manage: false }]);
    renderPage();
    expect(await screen.findByText(announcement.title)).toBeInTheDocument();
    for (const name of ["New announcement", "Edit announcement", "Pin announcement", "Delete announcement"]) {
      expect(screen.queryByRole("button", { name })).not.toBeInTheDocument();
    }
  });

  it("keeps students read-only without filtering out content returned by the API", async () => {
    listMyClassrooms.mockResolvedValue([{ ...classroom, membership: { role: "student", status: "approved" } }]);
    api.listAnnouncements.mockResolvedValue([{ ...announcement, class_course_id: 11, can_manage: false }]);
    renderPage();
    expect(await screen.findByText(announcement.title)).toBeInTheDocument();
    expect(screen.queryByRole("button", { name: "New announcement" })).not.toBeInTheDocument();
    expect(listClassCourses).toHaveBeenCalledWith(1);
  });

  it("creates an announcement with an active course and prevents duplicate submission", async () => {
    api.listAnnouncements.mockResolvedValue([]);
    const request = deferred();
    api.createAnnouncement.mockReturnValue(request.promise);
    renderPage();
    fireEvent.click(await screen.findByRole("button", { name: "New announcement" }));
    fillForm();
    expect(screen.getByLabelText(/Title/)).toHaveAttribute("maxlength", "200");
    expect(screen.getByRole("option", { name: "Entire class" })).toBeInTheDocument();
    expect(screen.queryByRole("option", { name: /CS101/ })).not.toBeInTheDocument();
    fireEvent.change(screen.getByLabelText("Scope"), { target: { value: "11" } });
    fireEvent.click(screen.getByLabelText("Pinned announcement"));
    const form = screen.getByLabelText(/Title/).closest("form");
    fireEvent.submit(form);
    fireEvent.submit(form);
    expect(api.createAnnouncement).toHaveBeenCalledTimes(1);
    expect(api.createAnnouncement).toHaveBeenCalledWith(1, {
      title: "Exam update", body: "Bring a calculator.", class_course_id: 11, is_pinned: true,
    });
    expect(screen.getByRole("button", { name: "Saving..." })).toBeDisabled();
    fireEvent.keyDown(document, { key: "Escape" });
    expect(screen.getByRole("dialog")).toBeInTheDocument();
    const created = { ...announcement, title: "Exam update", is_pinned: true, class_course_id: 11 };
    api.listAnnouncements.mockResolvedValue([created]);
    await act(async () => request.resolve(created));
    expect(await screen.findByText("Announcement saved.")).toBeInTheDocument();
    expect(screen.queryByRole("dialog")).not.toBeInTheDocument();
  });

  it("preserves a failed form and submits Entire class as null on retry", async () => {
    api.createAnnouncement.mockRejectedValueOnce({ response: { status: 422, data: {
      detail: [{ loc: ["body", "title"], msg: "Title is invalid" }],
    } } });
    api.createAnnouncement.mockResolvedValueOnce(announcement);
    renderPage();
    fireEvent.click(await screen.findByRole("button", { name: "New announcement" }));
    fillForm();
    fireEvent.click(screen.getByRole("button", { name: "Create announcement" }));
    expect(await screen.findByText("title: Title is invalid")).toBeInTheDocument();
    expect(screen.getByLabelText(/Title/)).toHaveValue("Exam update");
    expect(screen.getByLabelText(/Body/)).toHaveValue("Bring a calculator.");
    fireEvent.click(screen.getByRole("button", { name: "Create announcement" }));
    await waitFor(() => expect(screen.queryByRole("dialog")).not.toBeInTheDocument());
    expect(api.createAnnouncement).toHaveBeenLastCalledWith(1, expect.objectContaining({ class_course_id: null }));
  });

  it("edits, pins, unpins, and deletes only after confirmation", async () => {
    renderPage();
    fireEvent.click(await screen.findByRole("button", { name: "Edit announcement" }));
    const edited = { ...announcement, title: "New meeting time", body: "Meet at 10." };
    api.updateAnnouncement.mockResolvedValueOnce(edited);
    api.listAnnouncements.mockResolvedValue([edited]);
    fillForm(edited.title, edited.body);
    fireEvent.click(screen.getByRole("button", { name: "Save changes" }));
    expect(await screen.findByText(edited.title)).toBeInTheDocument();
    expect(api.updateAnnouncement).toHaveBeenCalledWith(10, {
      title: edited.title, body: edited.body, is_pinned: false, class_course_id: null,
    });
    const pinned = { ...edited, is_pinned: true };
    api.updateAnnouncement.mockResolvedValueOnce(pinned);
    api.listAnnouncements.mockResolvedValue([pinned]);
    fireEvent.click(screen.getByRole("button", { name: "Pin announcement" }));
    const unpin = await screen.findByRole("button", { name: "Unpin announcement" });
    await waitFor(() => expect(unpin).toBeEnabled());
    expect(api.updateAnnouncement).toHaveBeenLastCalledWith(10, { is_pinned: true });
    api.updateAnnouncement.mockResolvedValueOnce(edited);
    api.listAnnouncements.mockResolvedValue([edited]);
    fireEvent.click(unpin);
    await waitFor(() => expect(screen.getByRole("button", { name: "Pin announcement" })).toBeEnabled());
    expect(api.updateAnnouncement).toHaveBeenLastCalledWith(10, { is_pinned: false });
    fireEvent.click(screen.getByRole("button", { name: "Delete announcement" }));
    expect(api.deleteAnnouncement).not.toHaveBeenCalled();
    fireEvent.click(within(screen.getByRole("dialog")).getByRole("button", { name: "Cancel" }));
    expect(api.deleteAnnouncement).not.toHaveBeenCalled();
    fireEvent.click(screen.getByRole("button", { name: "Delete announcement" }));
    const deletion = deferred();
    api.deleteAnnouncement.mockReturnValue(deletion.promise);
    fireEvent.click(within(screen.getByRole("dialog")).getByRole("button", { name: "Delete announcement" }));
    expect(screen.getByRole("article")).toBeInTheDocument();
    await act(async () => deletion.resolve());
    expect(await screen.findByText("No announcements yet")).toBeInTheDocument();
    expect(api.deleteAnnouncement).toHaveBeenCalledWith(10);
  });

  it.each([403, 404, 503])("handles a %s list error without showing content and supports retry", async (status) => {
    api.listAnnouncements.mockRejectedValueOnce(apiError(status, "Secret internal details"));
    renderPage();
    expect(await screen.findByRole("alert")).not.toHaveTextContent("Secret internal details");
    expect(screen.queryByRole("article")).not.toBeInTheDocument();
    expect(screen.queryByRole("button", { name: "New announcement" })).not.toBeInTheDocument();
    fireEvent.click(screen.getByRole("button", { name: "Try again" }));
    expect(await screen.findByText(announcement.title)).toBeInTheDocument();
  });

  it("shows an exact-ID authorization error in the edit form without losing text", async () => {
    api.updateAnnouncement.mockRejectedValueOnce(apiError(403));
    renderPage();
    fireEvent.click(await screen.findByRole("button", { name: "Edit announcement" }));
    fillForm("Keep this text");
    fireEvent.click(screen.getByRole("button", { name: "Save changes" }));
    expect(await screen.findByRole("alert")).toHaveTextContent("You cannot perform this action");
    expect(screen.getByLabelText(/Title/)).toHaveValue("Keep this text");
  });

  it("does not show stale results or drafts after changing classrooms", async () => {
    const first = deferred();
    api.listAnnouncements.mockReturnValueOnce(first.promise).mockResolvedValueOnce([]);
    renderPage();
    fireEvent.click(screen.getByRole("link", { name: "Other classroom" }));
    expect(await screen.findByText("No announcements yet")).toBeInTheDocument();
    await act(async () => first.resolve([announcement]));
    expect(screen.queryByText(announcement.title)).not.toBeInTheDocument();
    expect(api.listAnnouncements).toHaveBeenCalledWith(2);
  });

  it("does not show create controls for an empty student collection", async () => {
    listMyClassrooms.mockResolvedValue([{ ...classroom, membership: { role: "student", status: "approved" } }]);
    api.listAnnouncements.mockResolvedValue([]);
    renderPage();
    expect(await screen.findByText("No announcements yet")).toBeInTheDocument();
    expect(screen.queryByRole("button", { name: "New announcement" })).not.toBeInTheDocument();
  });
});
