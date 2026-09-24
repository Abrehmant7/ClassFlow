import { apiClient } from "./client.js";

/**
 * @typedef {Object} SearchResult
 * @property {'task'|'announcement'|'resource'} entity_type
 * @property {number} id
 * @property {string} title
 * @property {string} preview
 * @property {number|null} classroom_id
 * @property {number|null} class_course_id
 * @property {string|null} date
 * @property {string|null} task_type
 * @property {string|null} priority
 * @property {string|null} status
 * @property {string} action_url
 */

/** @returns {Promise<{items: SearchResult[], total: number, page: number, page_size: number, total_pages: number}>} */
export async function searchContent(params) {
  const response = await apiClient.get("/search", { params });
  return response.data;
}
