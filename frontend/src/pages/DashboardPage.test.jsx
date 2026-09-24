import { fireEvent, render, screen, within } from "@testing-library/react";
import { MemoryRouter } from "react-router-dom";
import { beforeEach, describe, expect, it, vi } from "vitest";

import { getDashboard } from "../api/dashboard.js";
import useNotifications from "../notifications/useNotifications.js";
import { apiError, dashboard } from "../test/module7Fixtures.js";
import DashboardPage from "./DashboardPage.jsx";

vi.mock("../api/dashboard.js", () => ({ getDashboard: vi.fn() }));
vi.mock("../notifications/useNotifications.js", () => ({ default: vi.fn() }));
vi.mock("./PersonalFeedPage.jsx", () => ({ default: () => <div>Existing personal feed</div> }));

function renderPage() {
  return render(<MemoryRouter><DashboardPage /></MemoryRouter>);
}

describe("dashboard", () => {
  beforeEach(() => {
    vi.resetAllMocks();
    getDashboard.mockResolvedValue(dashboard);
    useNotifications.mockReturnValue({ markRead: vi.fn().mockResolvedValue({}) });
  });

  it("requests the browser timezone and shows backend summary, previews, links, and feed", async () => {
    renderPage();
    expect(screen.getByText("Loading dashboard summary...")).toBeInTheDocument();
    expect(await screen.findByText("Database assignment")).toBeInTheDocument();
    expect(getDashboard).toHaveBeenCalledWith(Intl.DateTimeFormat().resolvedOptions().timeZone);
    const overview = screen.getByRole("region", { name: "Dashboard overview" });
    expect(within(overview).getByText("2")).toBeInTheDocument();
    expect(within(overview).getByText("5")).toBeInTheDocument();
    expect(within(overview).getByText("1")).toBeInTheDocument();
    expect(screen.getByRole("region", { name: "Tasks due today" })).toContainElement(screen.getByRole("link", { name: "Database assignment" }));
    expect(screen.getByRole("link", { name: "Database assignment" })).toHaveAttribute("href", "/tasks/20");
    expect(screen.getByText("Lab writeup")).toBeInTheDocument();
    expect(screen.getByText("Old quiz")).toBeInTheDocument();
    expect(screen.getByRole("link", { name: "Class meeting" })).toHaveAttribute("href", "/classes/4?tab=announcements");
    expect(screen.getByRole("link", { name: /New task/ })).toHaveAttribute("href", "/tasks/20");
    expect(screen.getByRole("link", { name: /Ada/ })).toHaveAttribute("href", "/classes/4/members");
    expect(screen.getByText("Existing personal feed")).toBeInTheDocument();
  });

  it("hides pending requests when the count is zero and shows empty previews", async () => {
    getDashboard.mockResolvedValue({ ...dashboard, task_summary: { due_today: 0, upcoming: 0, overdue: 0 },
      tasks_due_today: [], upcoming_tasks: [], overdue_tasks: [], recent_announcements: [],
      recent_notifications: [], pending_membership_request_count: 0, pending_membership_requests: [] });
    renderPage();
    expect(await screen.findByText("No tasks due today")).toBeInTheDocument();
    expect(screen.getByText("No upcoming tasks")).toBeInTheDocument();
    expect(screen.getByText("No overdue tasks")).toBeInTheDocument();
    expect(screen.getByText("No recent announcements")).toBeInTheDocument();
    expect(screen.getByText("No recent notifications")).toBeInTheDocument();
    expect(screen.queryByRole("region", { name: "Pending membership requests" })).not.toBeInTheDocument();
    expect(screen.getByText("Existing personal feed")).toBeInTheDocument();
  });

  it("keeps the feed available during a dashboard failure and retries", async () => {
    getDashboard.mockRejectedValueOnce(apiError(503, "Sensitive backend error")).mockResolvedValueOnce(dashboard);
    renderPage();
    expect(await screen.findByRole("alert")).toHaveTextContent("temporarily unavailable");
    expect(screen.queryByText("Sensitive backend error")).not.toBeInTheDocument();
    expect(screen.getByText("Existing personal feed")).toBeInTheDocument();
    fireEvent.click(screen.getByRole("button", { name: "Try again" }));
    expect(await screen.findByText("Database assignment")).toBeInTheDocument();
  });

});
