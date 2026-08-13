import { apiClient } from "./client.js";

export async function listMyClassrooms() {
  const response = await apiClient.get("/classes/mine");
  return response.data;
}

export async function createClassroom(payload) {
  const response = await apiClient.post("/classes", payload);
  return response.data;
}

export async function getClassroom(classId) {
  const response = await apiClient.get(`/classes/${classId}`);
  return response.data;
}

export async function joinClassroom(classId, joinCode) {
  const response = await apiClient.post(`/classes/${classId}/join`, {
    join_code: joinCode,
  });
  return response.data;
}

export async function listJoinRequests(classId) {
  const response = await apiClient.get(`/classes/${classId}/requests`);
  return response.data;
}

export async function listClassMembers(classId) {
  const response = await apiClient.get(`/classes/${classId}/members`);
  return response.data;
}
