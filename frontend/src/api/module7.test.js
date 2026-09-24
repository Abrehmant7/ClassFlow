import { beforeEach, describe, expect, it, vi } from "vitest";

import { apiClient } from "./client.js";
import { getDashboard } from "./dashboard.js";
import { getUnreadCount, listNotifications, markAllNotificationsRead, markNotificationRead, markNotificationUnread } from "./notifications.js";
import { searchContent } from "./search.js";

vi.mock("./client.js", () => ({ apiClient: { get: vi.fn(), patch: vi.fn(), post: vi.fn() } }));

describe("Module 7 API helpers", () => {
  beforeEach(() => {
    vi.resetAllMocks();
    for (const method of ["get", "patch", "post"]) apiClient[method].mockResolvedValue({ data: { ok: true } });
  });

  it("uses recipient-scoped notification endpoints and pagination filters", async () => {
    await listNotifications({ unread_only: true, event_type: "task_created", page: 2, page_size: 5 });
    await getUnreadCount();
    await markNotificationRead(1);
    await markNotificationUnread(1);
    await markAllNotificationsRead();
    expect(apiClient.get).toHaveBeenNthCalledWith(1, "/notifications", { params: {
      unread_only: true, event_type: "task_created", page: 2, page_size: 5,
    } });
    expect(apiClient.get).toHaveBeenNthCalledWith(2, "/notifications/unread-count");
    expect(apiClient.patch).toHaveBeenNthCalledWith(1, "/notifications/1/read");
    expect(apiClient.patch).toHaveBeenNthCalledWith(2, "/notifications/1/unread");
    expect(apiClient.post).toHaveBeenCalledWith("/notifications/read-all");
  });

  it("keeps search entity type and task type separate", async () => {
    await searchContent({ q: "database", entity_type: "task", task_type: "assignment", page: 1 });
    expect(apiClient.get).toHaveBeenCalledWith("/search", { params: {
      q: "database", entity_type: "task", task_type: "assignment", page: 1,
    } });
  });

  it("sends the given browser timezone to dashboard", async () => {
    await getDashboard("America/New_York");
    expect(apiClient.get).toHaveBeenCalledWith("/dashboard", { params: { timezone: "America/New_York" } });
  });
});
