import { apiClient } from "./client.js";

function cleanParams(params) {
  return Object.fromEntries(
    Object.entries(params).filter(([, value]) => value !== "" && value != null),
  );
}

export async function fetchFeed(params) {
  const response = await apiClient.get("/feed", {
    params: cleanParams(params),
  });
  return response.data;
}

export async function fetchFeedSummary(timezone) {
  const response = await apiClient.get("/feed/summary", {
    params: { timezone },
  });
  return response.data;
}

export async function fetchFeedFilterOptions() {
  const response = await apiClient.get("/feed/filter-options");
  return response.data;
}
