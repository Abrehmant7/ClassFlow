import { apiClient } from "./client.js";

export async function sendClassChatMessage(classId, message) {
  const response = await apiClient.post(`/classes/${classId}/chat`, {
    message,
  });
  return response.data;
}

export async function sendClassChatFileMessage(classId, message, file) {
  const formData = new FormData();
  formData.append("message", message);
  formData.append("file", file);

  const response = await apiClient.post(`/classes/${classId}/chat/file`, formData);
  return response.data;
}
