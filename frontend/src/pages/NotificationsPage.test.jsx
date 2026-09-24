import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { MemoryRouter, Route, Routes, useLocation } from "react-router-dom";
import { beforeEach, describe, expect, it, vi } from "vitest";

import { listNotifications } from "../api/notifications.js";
import useNotifications from "../notifications/useNotifications.js";
import { notification } from "../test/module7Fixtures.js";
import NotificationsPage from "./NotificationsPage.jsx";

vi.mock("../api/notifications.js", () => ({ listNotifications: vi.fn() }));
vi.mock("../notifications/useNotifications.js", () => ({ default: vi.fn() }));

function Location() {
  const location = useLocation();
  return <div data-testid="location">{location.pathname}{location.search}</div>;
}

function renderPage(initial = "/notifications") {
  return render(<MemoryRouter initialEntries={[initial]}>
    <Location />
    <Routes><Route element={<NotificationsPage />} path="/notifications" /><Route element={<p>Task destination</p>} path="/tasks/:taskId" /></Routes>
  </MemoryRouter>);
}

describe("notifications page", () => {
  let markRead;
  let markUnread;
  let markAllRead;
  beforeEach(() => {
    vi.resetAllMocks();
    listNotifications.mockResolvedValue({ items: [notification], total: 41, page: 1, page_size: 20 });
    markRead = vi.fn().mockResolvedValue({ ...notification, is_read: true });
    markUnread = vi.fn().mockResolvedValue({ ...notification, is_read: false });
    markAllRead = vi.fn().mockResolvedValue({ updated_count: 1 });
    useNotifications.mockReturnValue({ markRead, markUnread, markAllRead });
  });

  it("paginates and filters unread notifications by event type", async () => {
    renderPage();
    expect(await screen.findByRole("link", { name: /New task/ })).toBeInTheDocument();
    fireEvent.change(screen.getByLabelText("Show"), { target: { value: "true" } });
    await waitFor(() => expect(listNotifications).toHaveBeenLastCalledWith({ page: 1, page_size: 20, unread_only: true }));
    fireEvent.change(screen.getByLabelText("Event type"), { target: { value: "task_created" } });
    await waitFor(() => expect(listNotifications).toHaveBeenLastCalledWith({ page: 1, page_size: 20, unread_only: true, event_type: "task_created" }));
    fireEvent.click(screen.getByRole("button", { name: "Next" }));
    await waitFor(() => expect(listNotifications).toHaveBeenLastCalledWith({ page: 2, page_size: 20, unread_only: true, event_type: "task_created" }));
    expect(screen.getByTestId("location")).toHaveTextContent("page=2");
  });

  it("marks read, unread, all read, and opens the supplied action URL", async () => {
    listNotifications.mockResolvedValueOnce({ items: [notification], total: 1, page: 1, page_size: 20 })
      .mockResolvedValue({ items: [{ ...notification, is_read: true }], total: 1, page: 1, page_size: 20 });
    renderPage();
    fireEvent.click(await screen.findByRole("button", { name: "Mark read" }));
    await waitFor(() => expect(markRead).toHaveBeenCalledWith(notification));
    await screen.findByRole("button", { name: "Mark unread" });
    fireEvent.click(screen.getByRole("button", { name: "Mark unread" }));
    await waitFor(() => expect(markUnread).toHaveBeenCalled());
    fireEvent.click(screen.getByRole("button", { name: "Mark all as read" }));
    await waitFor(() => expect(markAllRead).toHaveBeenCalledTimes(1));
    fireEvent.click(screen.getByRole("link", { name: /New task/ }));
    expect(await screen.findByText("Task destination")).toBeInTheDocument();
  });

  it("shows an empty state and a retryable API error", async () => {
    listNotifications.mockRejectedValueOnce({ response: { status: 503, data: { detail: "Internal" } } })
      .mockResolvedValueOnce({ items: [], total: 0, page: 1, page_size: 20 });
    renderPage();
    expect(await screen.findByRole("alert")).not.toHaveTextContent("Internal");
    fireEvent.click(screen.getByRole("button", { name: "Try again" }));
    expect(await screen.findByText("No notifications found")).toBeInTheDocument();
  });
});
