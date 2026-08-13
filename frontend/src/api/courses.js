import { apiClient } from "./client.js";

export async function listCourses(search = "") {
  const response = await apiClient.get("/courses", {
    params: search ? { search } : {},
  });
  return response.data;
}

export async function createCourse(payload) {
  const response = await apiClient.post("/courses", payload);
  return response.data;
}

export async function listClassCourses(classId, includeInactive = false) {
  const response = await apiClient.get(`/classes/${classId}/courses`, {
    params: includeInactive ? { include_inactive: true } : {},
  });
  return response.data;
}

export async function addClassCourse(classId, payload) {
  const response = await apiClient.post(`/classes/${classId}/courses`, payload);
  return response.data;
}

export async function updateClassCourse(classCourseId, payload) {
  const response = await apiClient.patch(
    `/class-courses/${classCourseId}`,
    payload,
  );
  return response.data;
}

export async function deleteClassCourse(classCourseId) {
  await apiClient.delete(`/class-courses/${classCourseId}`);
}

export async function listMyCourses(classId) {
  const response = await apiClient.get(`/classes/${classId}/my-courses`);
  return response.data;
}

export async function registerClassCourse(classCourseId) {
  const response = await apiClient.post(
    `/class-courses/${classCourseId}/register`,
  );
  return response.data;
}

export async function dropClassCourse(classCourseId) {
  await apiClient.delete(`/class-courses/${classCourseId}/register`);
}
