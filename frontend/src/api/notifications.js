import { apiClient } from "./client.js";

/**
 * @typedef {Object} Notification
 * @property {number} id
 * @property {string} event_type
 * @property {string} title
 * @property {string} message
 * @property {number|null} classroom_id
 * @property {string} source_type
 * @property {number} source_id
 * @property {string} action_url
 * @property {boolean} is_read
 * @property {string|null} read_at
 * @property {string} created_at
 */

/** @returns {Promise<{items: Notification[], total: number, page: number, page_size: number}>} */
export async function listNotifications(params = {}) {
  const response = await apiClient.get("/notifications", { params });
  return response.data;
}

/** @returns {Promise<{unread_count: number}>} */
export async function getUnreadCount() {
  const response = await apiClient.get("/notifications/unread-count");
  return response.data;
}

/** @param {number} id @returns {Promise<Notification>} */
export async function markNotificationRead(id) {
  const response = await apiClient.patch(`/notifications/${id}/read`);
  return response.data;
}

/** @param {number} id @returns {Promise<Notification>} */
export async function markNotificationUnread(id) {
  const response = await apiClient.patch(`/notifications/${id}/unread`);
  return response.data;
}

/** @returns {Promise<{updated_count: number}>} */
export async function markAllNotificationsRead() {
  const response = await apiClient.post("/notifications/read-all");
  return response.data;
}
