export const TASK_TYPES = [
  "assignment",
  "quiz",
  "lab",
  "project",
  "presentation",
  "exam",
  "other",
];

export const TASK_PRIORITIES = ["low", "medium", "high", "urgent"];

export function formatTaskLabel(value) {
  return String(value || "unknown").replaceAll("_", " ");
}

export function formatDeadline(value) {
  if (!value) return "No deadline";
  return new Intl.DateTimeFormat(undefined, {
    dateStyle: "medium",
    timeStyle: "short",
  }).format(new Date(value));
}

export function toApiDeadline(value) {
  if (!value) return null;
  return new Date(value).toISOString();
}

export function toDateTimeLocal(value) {
  if (!value) return "";
  const date = new Date(value);
  const offsetMs = date.getTimezoneOffset() * 60 * 1000;
  return new Date(date.getTime() - offsetMs).toISOString().slice(0, 16);
}

export function getCreatorName(creator) {
  if (!creator) return "Unknown";
  if (creator.name) return creator.name;
  const fullName = [creator.first_name, creator.last_name]
    .filter(Boolean)
    .join(" ");
  return fullName || creator.username || `User #${creator.id}`;
}

export function formatFileSize(bytes) {
  if (!Number.isFinite(bytes)) return "";
  if (bytes < 1024) return `${bytes} B`;
  if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`;
  return `${(bytes / (1024 * 1024)).toFixed(1)} MB`;
}
