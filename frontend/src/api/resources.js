import { apiClient } from "./client.js";

/**
 * @typedef {Object} Resource
 * @property {number} id
 * @property {number} classroom_id
 * @property {number|null} class_course_id
 * @property {number} uploaded_by_user_id
 * @property {string} title
 * @property {string|null} description
 * @property {string} file_name
 * @property {string} content_type
 * @property {number|null} file_size
 * @property {boolean} is_enabled
 * @property {'pending'|'processing'|'indexed'|'failed'} indexing_status
 * @property {string|null} indexing_error
 * @property {string|null} indexed_at
 * @property {string} created_at
 * @property {string} updated_at
 * @property {boolean} can_manage
 */
/**
 * @typedef {Object} ResourceUpload
 * @property {string} title
 * @property {string|null} [description]
 * @property {number|null} [class_course_id]
 * @property {File} file
 */
/**
 * @typedef {Object} ResourceUpdate
 * @property {string} [title]
 * @property {string|null} [description]
 * @property {boolean} [is_enabled]
 */

/** @param {number} classId @returns {Promise<Resource[]>} */
export async function listResources(classId) {
  const response = await apiClient.get(`/classes/${classId}/resources`);
  return response.data;
}

/** @param {number} id @returns {Promise<Resource>} */
export async function getResource(id) {
  const response = await apiClient.get(`/resources/${id}`);
  return response.data;
}

/**
 * @param {number} classId
 * @param {ResourceUpload} payload
 * @param {import('axios').AxiosRequestConfig['onUploadProgress']} [onUploadProgress]
 * @returns {Promise<Resource>}
 */
export async function uploadResource(classId, payload, onUploadProgress) {
  const formData = new FormData();
  formData.append("title", payload.title);
  if (payload.description) formData.append("description", payload.description);
  if (payload.class_course_id != null) {
    formData.append("class_course_id", String(payload.class_course_id));
  }
  formData.append("file", payload.file);
  // Let the browser supply Content-Type and its multipart boundary.
  const response = await apiClient.post(`/classes/${classId}/resources`, formData, {
    onUploadProgress,
  });
  return response.data;
}

/** @param {number} id @param {ResourceUpdate} payload @returns {Promise<Resource>} */
export async function updateResource(id, payload) {
  const response = await apiClient.patch(`/resources/${id}`, payload);
  return response.data;
}

/** @param {number} id @returns {Promise<void>} */
export async function deleteResource(id) {
  await apiClient.delete(`/resources/${id}`);
}

/** @param {number} id @returns {Promise<Resource>} */
export async function reindexResource(id) {
  const response = await apiClient.post(`/resources/${id}/reindex`);
  return response.data;
}

/** @param {string|undefined} disposition @param {string} fallback @returns {string} */
function downloadFilename(disposition, fallback) {
  const extended = disposition?.match(/filename\*\s*=\s*UTF-8'[^']*'([^;]+)/i);
  let filename;
  if (extended) {
    try {
      filename = decodeURIComponent(extended[1].trim());
    } catch { /* Fall back to filename or the resource metadata. */ }
  }
  if (!filename) {
    const regular = disposition?.match(/(?:^|;)\s*filename\s*=\s*(?:"((?:\\.|[^"\\])*)"|([^;]+))/i);
    filename = regular?.[1]?.replace(/\\(.)/g, "$1") || regular?.[2]?.trim();
  }
  return (filename || fallback).split(/[\\/]/).pop() || fallback;
}

/** @param {Pick<Resource, 'id'|'file_name'>} resource @returns {Promise<void>} */
export async function downloadResource(resource) {
  let response;
  try {
    response = await apiClient.get(`/resources/${resource.id}/download`, { responseType: "blob" });
  } catch (error) {
    // Axios also returns error bodies as blobs for a blob request.
    if (error.response?.data instanceof Blob) {
      try {
        const body = await new Promise((resolve, reject) => {
          const reader = new FileReader();
          reader.onload = () => resolve(reader.result);
          reader.onerror = () => reject(reader.error);
          reader.readAsText(error.response.data);
        });
        error.response.data = JSON.parse(body);
      } catch { /* Status-based error handling still works for non-JSON responses. */ }
    }
    throw error;
  }

  const url = window.URL.createObjectURL(response.data);
  const link = document.createElement("a");
  try {
    link.href = url;
    link.download = downloadFilename(response.headers["content-disposition"], resource.file_name);
    document.body.appendChild(link);
    link.click();
  } finally {
    link.remove();
    // Allow the browser to start the download before releasing the object URL.
    window.setTimeout(() => window.URL.revokeObjectURL(url), 1000);
  }
}
