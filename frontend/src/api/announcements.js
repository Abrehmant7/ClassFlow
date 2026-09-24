import { apiClient } from "./client.js";

/**
 * @typedef {Object} Announcement
 * @property {number} id
 * @property {number} classroom_id
 * @property {number|null} class_course_id
 * @property {number} created_by_user_id
 * @property {string} title
 * @property {string} body
 * @property {boolean} is_pinned
 * @property {string} created_at
 * @property {string} updated_at
 * @property {boolean} can_manage
 */
/**
 * @typedef {Object} AnnouncementCreate
 * @property {string} title
 * @property {string} body
 * @property {number|null} [class_course_id]
 * @property {boolean} [is_pinned]
 */

/** @param {number} classId @returns {Promise<Announcement[]>} */
export async function listAnnouncements(classId) {
  const response = await apiClient.get(`/classes/${classId}/announcements`);
  return response.data;
}

/** @param {number} id @returns {Promise<Announcement>} */
export async function getAnnouncement(id) {
  const response = await apiClient.get(`/announcements/${id}`);
  return response.data;
}

/** @param {number} classId @param {AnnouncementCreate} payload @returns {Promise<Announcement>} */
export async function createAnnouncement(classId, payload) {
  const response = await apiClient.post(`/classes/${classId}/announcements`, payload);
  return response.data;
}

/** @param {number} id @param {Partial<AnnouncementCreate>} payload @returns {Promise<Announcement>} */
export async function updateAnnouncement(id, payload) {
  const response = await apiClient.patch(`/announcements/${id}`, payload);
  return response.data;
}

/** @param {number} id @returns {Promise<void>} */
export async function deleteAnnouncement(id) {
  await apiClient.delete(`/announcements/${id}`);
}
