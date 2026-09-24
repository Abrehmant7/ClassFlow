import { apiClient } from "./client.js";

/**
 * @typedef {Object} DashboardData
 * @property {{due_today: number, upcoming: number, overdue: number}} task_summary
 * @property {Object[]} tasks_due_today
 * @property {Object[]} upcoming_tasks
 * @property {Object[]} overdue_tasks
 * @property {Object[]} recent_announcements
 * @property {number} unread_notification_count
 * @property {Object[]} recent_notifications
 * @property {number} pending_membership_request_count
 * @property {Object[]} pending_membership_requests
 */

/** @param {string} timezone @returns {Promise<DashboardData>} */
export async function getDashboard(timezone) {
  const response = await apiClient.get("/dashboard", { params: { timezone } });
  return response.data;
}
