import axios from "axios";

import {
  clearTokens,
  getAccessToken,
  getRefreshToken,
  setTokens,
} from "../auth/tokenStorage.js";

const apiBaseUrl = import.meta.env.VITE_API_BASE_URL || "/api/v1";

export const apiClient = axios.create({
  baseURL: apiBaseUrl,
  headers: {
    Accept: "application/json",
  },
});

let authExpiredHandler = null;
let refreshRequest = null;

export function setAuthExpiredHandler(handler) {
  authExpiredHandler = handler;
}

apiClient.interceptors.request.use((config) => {
  const accessToken = getAccessToken();

  if (accessToken) {
    config.headers.Authorization = `Bearer ${accessToken}`;
  }

  return config;
});

apiClient.interceptors.response.use(
  (response) => response,
  async (error) => {
    const originalRequest = error.config;
    const status = error.response?.status;
    const requestUrl = originalRequest?.url || "";
    const isAuthEndpoint =
      requestUrl.includes("/auth/login") ||
      requestUrl.includes("/auth/refresh") ||
      requestUrl.includes("/auth/logout");

    if (
      status !== 401 ||
      !originalRequest ||
      originalRequest._retry ||
      isAuthEndpoint
    ) {
      return Promise.reject(error);
    }

    const refreshToken = getRefreshToken();

    if (!refreshToken) {
      clearTokens();
      authExpiredHandler?.();
      return Promise.reject(error);
    }

    originalRequest._retry = true;

    try {
      if (!refreshRequest) {
        refreshRequest = axios
          .post(
            `${apiBaseUrl}/auth/refresh`,
            { refresh_token: refreshToken },
            {
              headers: {
                Accept: "application/json",
                "Content-Type": "application/json",
              },
            },
          )
          .finally(() => {
            refreshRequest = null;
          });
      }

      const response = await refreshRequest;
      setTokens(response.data);
      originalRequest.headers.Authorization = `Bearer ${response.data.access_token}`;

      return apiClient(originalRequest);
    } catch (refreshError) {
      clearTokens();
      authExpiredHandler?.();
      return Promise.reject(refreshError);
    }
  },
);
