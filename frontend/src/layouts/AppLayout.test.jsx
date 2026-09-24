import { fireEvent, render, screen } from "@testing-library/react";
import { MemoryRouter, Route, Routes } from "react-router-dom";
import { beforeEach, describe, expect, it, vi } from "vitest";

import * as notifications from "../api/notifications.js";
import { useAuth } from "../auth/useAuth.js";
import AppLayout from "./AppLayout.jsx";

vi.mock("../auth/useAuth.js", () => ({ useAuth: vi.fn() }));
vi.mock("../api/notifications.js", () => ({
  getUnreadCount: vi.fn(), listNotifications: vi.fn(), markNotificationRead: vi.fn(),
  markNotificationUnread: vi.fn(), markAllNotificationsRead: vi.fn(),
}));

describe("authenticated layout notification mounting", () => {
  beforeEach(() => {
    vi.resetAllMocks();
    useAuth.mockReturnValue({ isAuthenticated: false, user: null, logout: vi.fn() });
    notifications.getUnreadCount.mockResolvedValue({ unread_count: 0 });
    notifications.listNotifications.mockResolvedValue({ items: [], total: 0, page: 1, page_size: 5 });
  });

  it("does not fetch or poll notifications when logged out", () => {
    render(<MemoryRouter><Routes><Route element={<AppLayout />}>
      <Route element={<p>Public page</p>} path="/" />
    </Route></Routes></MemoryRouter>);
    expect(screen.getByText("Public page")).toBeInTheDocument();
    expect(screen.queryByRole("button", { name: /Notifications,.*unread/ })).not.toBeInTheDocument();
    fireEvent(window, new Event("focus"));
    expect(notifications.getUnreadCount).not.toHaveBeenCalled();
    expect(notifications.listNotifications).not.toHaveBeenCalled();
  });
});
