import { apiClient } from "./client.js";

export async function approveMembership(membershipId) {
  const response = await apiClient.patch(`/memberships/${membershipId}/approve`);
  return response.data;
}

export async function rejectMembership(membershipId) {
  const response = await apiClient.patch(`/memberships/${membershipId}/reject`);
  return response.data;
}

export async function removeMembership(membershipId) {
  await apiClient.delete(`/memberships/${membershipId}`);
}
