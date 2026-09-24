import { parseApiError } from "./errors.js";

export const NOTIFICATION_EVENTS = [
  ["membership_request", "Membership requests"],
  ["membership_approved", "Membership approvals"],
  ["membership_rejected", "Membership rejections"],
  ["task_created", "New tasks"],
  ["task_updated", "Task updates"],
  ["announcement_posted", "Announcements"],
  ["deadline_approaching", "Deadline reminders"],
];

export function formatLocalDate(value) {
  if (!value) return "";
  return new Intl.DateTimeFormat(undefined, { dateStyle: "medium", timeStyle: "short" }).format(new Date(value));
}

export function browserTimezone() {
  return Intl.DateTimeFormat().resolvedOptions().timeZone || "UTC";
}

export function parseModule7Error(error) {
  if (error.response?.status === 403) {
    return { message: "You cannot access this classroom or course filter.", items: [] };
  }
  if (error.response?.status === 404) {
    return { message: "This content is unavailable or could not be found.", items: [] };
  }
  if (error.response?.status >= 500) {
    return { message: "ClassFlow is temporarily unavailable. Please try again.", items: [] };
  }
  return parseApiError(error);
}
