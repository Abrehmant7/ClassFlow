import { act, fireEvent, render, screen, waitFor, within } from "@testing-library/react";
import { MemoryRouter, Route, Routes, useLocation } from "react-router-dom";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import * as api from "../api/notifications.js";
import { NotificationProvider } from "../notifications/NotificationProvider.jsx";
import { notification } from "../test/module7Fixtures.js";
import NotificationBell from "./NotificationBell.jsx";

vi.mock("../api/notifications.js", () => ({
  getUnreadCount: vi.fn(), listNotifications: vi.fn(), markNotificationRead: vi.fn(),
  markNotificationUnread: vi.fn(), markAllNotificationsRead: vi.fn(),
}));

function CurrentRoute() {
  const location = useLocation();
  return <p>Route: {location.pathname}</p>;
}

function renderBell() {
  return render(
    <MemoryRouter initialEntries={["/dashboard"]}>
      <NotificationProvider>
        <NotificationBell />
        <Routes>
          <Route element={<CurrentRoute />} path="/dashboard" />
          <Route element={<CurrentRoute />} path="/tasks/:taskId" />
        </Routes>
      </NotificationProvider>
    </MemoryRouter>,
  );
}

describe("notification bell", () => {
  beforeEach(() => {
    vi.resetAllMocks();
    api.getUnreadCount.mockResolvedValue({ unread_count: 3 });
    api.listNotifications.mockResolvedValue({ items: [notification, ...[2, 3, 4, 5].map((id) => ({ ...notification, id, title: `Notice ${id}` }))], total: 5, page: 1, page_size: 5 });
    api.markNotificationRead.mockResolvedValue({ ...notification, is_read: true, read_at: "2026-09-24T12:05:00Z" });
    api.markAllNotificationsRead.mockResolvedValue({ updated_count: 3 });
  });

  afterEach(() => { vi.restoreAllMocks(); });

  it("shows an unread badge and exactly five recent recipient notifications", async () => {
    renderBell();
    expect(await screen.findByRole("button", { name: "Notifications, 3 unread" })).toBeInTheDocument();
    fireEvent.click(screen.getByRole("button", { name: "Notifications, 3 unread" }));
    const popover = screen.getByRole("region", { name: "Recent notifications" });
    expect(within(popover).getAllByRole("article")).toHaveLength(5);
    expect(api.listNotifications).toHaveBeenCalledWith({ page: 1, page_size: 5 });
    expect(within(popover).getByRole("link", { name: "View all" })).toHaveAttribute("href", "/notifications");
    expect(within(popover).getAllByLabelText("Unread")).toHaveLength(5);
  });

  it("marks an opened notification read before navigating and updates the badge", async () => {
    renderBell();
    fireEvent.click(await screen.findByRole("button", { name: "Notifications, 3 unread" }));
    fireEvent.click(screen.getByRole("link", { name: /New task/ }));
    await waitFor(() => expect(api.markNotificationRead).toHaveBeenCalledWith(1));
    expect(await screen.findByText("Route: /tasks/20")).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Notifications, 2 unread" })).toBeInTheDocument();
    expect(screen.queryByRole("region", { name: "Recent notifications" })).not.toBeInTheDocument();
  });

  it("marks all as read without negative counts and supports Escape focus", async () => {
    renderBell();
    const bell = await screen.findByRole("button", { name: "Notifications, 3 unread" });
    fireEvent.click(bell);
    fireEvent.click(screen.getByRole("button", { name: "Mark all as read" }));
    await waitFor(() => expect(screen.getByRole("button", { name: "Notifications, 0 unread" })).toBeInTheDocument());
    expect(api.markAllNotificationsRead).toHaveBeenCalledTimes(1);
    expect(screen.queryByLabelText("Unread")).not.toBeInTheDocument();
    fireEvent.keyDown(document, { key: "Escape" });
    expect(screen.queryByRole("region", { name: "Recent notifications" })).not.toBeInTheDocument();
    expect(bell).toHaveFocus();
  });

  it("polls once per minute, refreshes on focus, and removes both on unmount", async () => {
    const interval = vi.spyOn(window, "setInterval");
    const clear = vi.spyOn(window, "clearInterval");
    const { unmount } = renderBell();
    await screen.findByRole("button", { name: "Notifications, 3 unread" });
    await waitFor(() => expect(api.listNotifications).toHaveBeenCalledTimes(1));
    const pollingTimers = interval.mock.calls.filter(([, delay]) => delay === 60_000);
    expect(pollingTimers).toHaveLength(1);
    await act(async () => { await pollingTimers[0][0](); });
    expect(api.listNotifications).toHaveBeenCalledTimes(2);
    await act(async () => { window.dispatchEvent(new Event("focus")); });
    expect(api.listNotifications).toHaveBeenCalledTimes(3);
    unmount();
    const pollingIndex = interval.mock.calls.findIndex(([, delay]) => delay === 60_000);
    expect(clear).toHaveBeenCalledWith(interval.mock.results[pollingIndex].value);
    window.dispatchEvent(new Event("focus"));
    expect(api.listNotifications).toHaveBeenCalledTimes(3);
  });

  it("shows load and retry errors without displaying another user's data", async () => {
    api.listNotifications.mockRejectedValueOnce({ response: { status: 403, data: { detail: "Other user data" } } })
      .mockResolvedValueOnce({ items: [], total: 0, page: 1, page_size: 5 });
    renderBell();
    fireEvent.click(await screen.findByRole("button", { name: "Notifications, 0 unread" }));
    expect(await screen.findByRole("alert")).not.toHaveTextContent("Other user data");
    fireEvent.click(screen.getByRole("button", { name: "Try again" }));
    expect(await screen.findByText("No notifications yet.")).toBeInTheDocument();
  });
});
