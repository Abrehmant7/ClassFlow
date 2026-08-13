import { apiClient } from "./client.js";

export async function registerUser(payload) {
  const response = await apiClient.post("/auth/register", payload);
  return response.data;
}

export async function loginUser({ username, password }) {
  const body = new URLSearchParams();
  body.set("username", username);
  body.set("password", password);

  const response = await apiClient.post("/auth/login", body, {
    headers: {
      "Content-Type": "application/x-www-form-urlencoded",
    },
  });

  return response.data;
}

export async function getCurrentUser() {
  const response = await apiClient.get("/users/me");
  return response.data;
}

export async function logoutUser(refreshToken) {
  const response = await apiClient.post("/auth/logout", {
    refresh_token: refreshToken,
  });
  return response.data;
}
