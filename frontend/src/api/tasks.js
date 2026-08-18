import { apiClient } from "./client.js";

export async function listTasks(classId, includeClosed = false) {
  const response = await apiClient.get(`/classes/${classId}/tasks`, {
    params: includeClosed ? { include_closed: true } : {},
  });
  return response.data;
}

export async function createTask(classId, payload) {
  const response = await apiClient.post(`/classes/${classId}/tasks`, payload);
  return response.data;
}

export async function createPersonalTask(payload) {
  const response = await apiClient.post("/personal-tasks", payload);
  return response.data;
}

export async function getTask(taskId) {
  const response = await apiClient.get(`/tasks/${taskId}`);
  return response.data;
}

export async function updateTask(taskId, payload) {
  const response = await apiClient.patch(`/tasks/${taskId}`, payload);
  return response.data;
}

export async function deleteTask(taskId) {
  await apiClient.delete(`/tasks/${taskId}`);
}

export async function updateTaskProgress(taskId, status) {
  const response = await apiClient.put(`/tasks/${taskId}/progress`, { status });
  return response.data;
}

export async function completePersonalTask(taskId) {
  const response = await apiClient.put(`/personal-tasks/${taskId}/complete`);
  return response.data;
}

export async function reopenPersonalTask(taskId) {
  const response = await apiClient.put(`/personal-tasks/${taskId}/reopen`);
  return response.data;
}

export async function uploadTaskAttachment(taskId, file) {
  const formData = new FormData();
  formData.append("file", file);

  const response = await apiClient.post(
    `/tasks/${taskId}/attachments`,
    formData,
    {
      headers: {
        "Content-Type": "multipart/form-data",
      },
    },
  );
  return response.data;
}

export async function listTaskAttachments(taskId) {
  const response = await apiClient.get(`/tasks/${taskId}/attachments`);
  return response.data;
}

export async function downloadTaskAttachment(attachment) {
  const response = await apiClient.get(
    `/attachments/${attachment.id}/download`,
    {
      responseType: "blob",
    },
  );

  const url = window.URL.createObjectURL(response.data);
  const link = document.createElement("a");
  link.href = url;
  link.download = attachment.file_name;
  document.body.appendChild(link);
  link.click();
  link.remove();
  window.URL.revokeObjectURL(url);
}

export async function deleteTaskAttachment(attachmentId) {
  await apiClient.delete(`/attachments/${attachmentId}`);
}
