import { act, fireEvent, render, screen, waitFor, within } from "@testing-library/react";
import { MemoryRouter, Route, Routes, useLocation } from "react-router-dom";
import { beforeEach, describe, expect, it, vi } from "vitest";

import { listMyClassrooms } from "../api/classrooms.js";
import { listClassCourses, listMyCourses } from "../api/courses.js";
import { searchContent } from "../api/search.js";
import { apiError, classCourse, classroom, deferred, searchResults } from "../test/module7Fixtures.js";
import SearchPage from "./SearchPage.jsx";

vi.mock("../api/classrooms.js", () => ({ listMyClassrooms: vi.fn() }));
vi.mock("../api/courses.js", () => ({ listClassCourses: vi.fn(), listMyCourses: vi.fn() }));
vi.mock("../api/search.js", () => ({ searchContent: vi.fn() }));

function Location() {
  const location = useLocation();
  return <div data-testid="location">{location.pathname}{location.search}</div>;
}

function renderPage(initial = "/search") {
  return render(<MemoryRouter initialEntries={[initial]}>
    <Location />
    <Routes>
      <Route element={<SearchPage />} path="/search" />
      <Route element={<p>Task destination</p>} path="/tasks/:taskId" />
    </Routes>
  </MemoryRouter>);
}

describe("global search", () => {
  beforeEach(() => {
    vi.resetAllMocks();
    listMyClassrooms.mockResolvedValue([classroom, { ...classroom, id: 5, name: "Pending class", membership: { role: "student", status: "pending" } }]);
    listClassCourses.mockResolvedValue([classCourse]);
    listMyCourses.mockResolvedValue([]);
    searchContent.mockResolvedValue(searchResults);
  });

  it("does not send empty terms, submits trimmed keywords, and limits filter choices to accessible classes", async () => {
    renderPage();
    expect(screen.getByText("Start a search")).toBeInTheDocument();
    fireEvent.change(screen.getByLabelText("Search terms"), { target: { value: "   " } });
    fireEvent.click(screen.getByRole("button", { name: "Search" }));
    expect(searchContent).not.toHaveBeenCalled();
    fireEvent.change(screen.getByLabelText("Search terms"), { target: { value: "  database  " } });
    fireEvent.click(screen.getByRole("button", { name: "Search" }));
    await waitFor(() => expect(searchContent).toHaveBeenCalledWith({ q: "database", entity_type: "all", page: 1, page_size: 20 }));
    expect(await screen.findByText("3 results")).toBeInTheDocument();
    expect(screen.getByRole("option", { name: "Computer Science" })).toBeInTheDocument();
    expect(screen.queryByRole("option", { name: "Pending class" })).not.toBeInTheDocument();
    expect(screen.getByRole("option", { name: "CS201 - Data Structures" })).toBeInTheDocument();
    expect(screen.getByTestId("location")).toHaveTextContent("q=database");
  });

  it("renders all entity kinds with backend action URLs and only task metadata", async () => {
    renderPage("/search?q=database");
    expect(await screen.findByText("3 results")).toBeInTheDocument();
    const articles = screen.getAllByRole("article");
    expect(articles).toHaveLength(3);
    expect(within(articles[0]).getByText("Task")).toBeInTheDocument();
    expect(within(articles[0]).getByText("assignment")).toBeInTheDocument();
    expect(within(articles[0]).getByText("high")).toBeInTheDocument();
    expect(within(articles[0]).getByText("active")).toBeInTheDocument();
    expect(within(articles[1]).getByText("Announcement")).toBeInTheDocument();
    expect(within(articles[1]).queryByText("assignment")).not.toBeInTheDocument();
    expect(within(articles[2]).getByText("Resource")).toBeInTheDocument();
    expect(within(articles[0]).getByRole("link", { name: "Database assignment" })).toHaveAttribute("href", "/tasks/20");
    expect(within(articles[1]).getByRole("link", { name: "Class meeting" })).toHaveAttribute("href", "/classes/4?tab=announcements");
    expect(within(articles[2]).getByRole("link", { name: "Course notes" })).toHaveAttribute("href", "/classes/4?tab=resources&resource=9");
    fireEvent.click(within(articles[0]).getByRole("link", { name: "Database assignment" }));
    expect(await screen.findByText("Task destination")).toBeInTheDocument();
  });

  it("sends filters, keeps entity_type distinct from task_type, and resets page to one", async () => {
    searchContent.mockResolvedValue({ ...searchResults, total: 40, total_pages: 2 });
    renderPage("/search?q=database&page=2&entity_type=task");
    await screen.findByText("40 results");
    fireEvent.change(screen.getByLabelText("Classroom"), { target: { value: "4" } });
    await waitFor(() => expect(searchContent).toHaveBeenLastCalledWith(expect.objectContaining({ q: "database", classroom_id: "4", entity_type: "task", page: 1 })));
    fireEvent.change(screen.getByLabelText("Course"), { target: { value: "12" } });
    fireEvent.change(screen.getByLabelText("From date"), { target: { value: "2026-09-01" } });
    fireEvent.change(screen.getByLabelText("To date"), { target: { value: "2026-09-30" } });
    fireEvent.change(screen.getByLabelText("Task type"), { target: { value: "assignment" } });
    fireEvent.change(screen.getByLabelText("Priority"), { target: { value: "high" } });
    fireEvent.change(screen.getByLabelText("Status"), { target: { value: "active" } });
    await waitFor(() => expect(searchContent).toHaveBeenLastCalledWith(expect.objectContaining({
      q: "database", entity_type: "task", class_course_id: "12", task_type: "assignment",
      priority: "high", status: "active", date_from: "2026-09-01", date_to: "2026-09-30", page: 1,
    })));
    fireEvent.click(screen.getByRole("tab", { name: "Resources" }));
    await waitFor(() => expect(searchContent).toHaveBeenLastCalledWith(expect.objectContaining({ entity_type: "resource", page: 1 })));
    expect(screen.queryByLabelText("Task type")).not.toBeInTheDocument();
    const last = searchContent.mock.lastCall[0];
    expect(last).not.toHaveProperty("task_type");
    expect(last).not.toHaveProperty("priority");
    expect(last).not.toHaveProperty("status");
    fireEvent.click(screen.getByRole("button", { name: "Clear filters" }));
    expect(screen.getByTestId("location")).toHaveTextContent("q=database");
    expect(screen.getByTestId("location")).not.toHaveTextContent("classroom_id");
  });

  it("paginates backend results and resets to page one for a new query", async () => {
    searchContent.mockImplementation(async (params) => ({ ...searchResults, total: 41,
      page: params.page, total_pages: 3 }));
    renderPage("/search?q=database");
    await screen.findByText("41 results");
    fireEvent.click(screen.getByRole("button", { name: "Next" }));
    await waitFor(() => expect(searchContent).toHaveBeenLastCalledWith(expect.objectContaining({ page: 2 })));
    expect(screen.getByTestId("location")).toHaveTextContent("page=2");
    fireEvent.change(screen.getByLabelText("Search terms"), { target: { value: "new topic" } });
    fireEvent.click(screen.getByRole("button", { name: "Search" }));
    await waitFor(() => expect(searchContent).toHaveBeenLastCalledWith(expect.objectContaining({ q: "new topic", page: 1 })));
    expect(screen.getByTestId("location")).not.toHaveTextContent("page=2");
  });

  it("populates student courses from active registrations only", async () => {
    listMyClassrooms.mockResolvedValue([{ ...classroom, membership: { role: "student", status: "approved" } }]);
    listMyCourses.mockResolvedValue([{ class_course_id: 12, class_course: classCourse },
      { class_course_id: 13, class_course: { ...classCourse, id: 13, is_active: false } }]);
    renderPage();
    expect(await screen.findByRole("option", { name: "CS201 - Data Structures" })).toBeInTheDocument();
    expect(screen.getAllByRole("option", { name: "CS201 - Data Structures" })).toHaveLength(1);
    expect(listClassCourses).not.toHaveBeenCalled();
  });

  it("shows no results, safe authorization errors, validation details, and retry", async () => {
    searchContent.mockResolvedValueOnce({ items: [], total: 0, page: 1, page_size: 20, total_pages: 0 })
      .mockRejectedValueOnce(apiError(403, "Private classroom exists"))
      .mockRejectedValueOnce(apiError(422, "Invalid date range"))
      .mockResolvedValueOnce(searchResults);
    renderPage("/search?q=database");
    expect(await screen.findByText("No results")).toBeInTheDocument();
    fireEvent.change(screen.getByLabelText("Classroom"), { target: { value: "4" } });
    expect(await screen.findByRole("alert")).not.toHaveTextContent("Private classroom exists");
    expect(screen.queryByText("Class meeting")).not.toBeInTheDocument();
    fireEvent.click(screen.getByRole("button", { name: "Try again" }));
    expect(await screen.findByText("Invalid date range")).toBeInTheDocument();
    fireEvent.click(screen.getByRole("button", { name: "Try again" }));
    expect(await screen.findByText("3 results")).toBeInTheDocument();
  });

  it("ignores a stale search response when filters change quickly", async () => {
    const first = deferred();
    searchContent.mockReturnValueOnce(first.promise).mockResolvedValueOnce(searchResults);
    renderPage("/search?q=database");
    await waitFor(() => expect(searchContent).toHaveBeenCalledTimes(1));
    fireEvent.click(screen.getByRole("tab", { name: "Announcements" }));
    expect(await screen.findByText("3 results")).toBeInTheDocument();
    await act(async () => first.resolve({ items: [], total: 0, page: 1, page_size: 20, total_pages: 0 }));
    expect(screen.getByText("3 results")).toBeInTheDocument();
  });
});
