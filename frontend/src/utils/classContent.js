import { isRepresentative } from "./classrooms.js";
import { formatCourseTitle } from "./courses.js";
import { parseApiError } from "./errors.js";

export const INDEXING_LABELS = {
  pending: "Waiting to index",
  processing: "Indexing",
  indexed: "Ready",
  failed: "Indexing failed",
};

export function contentScope(classCourseId, courses) {
  if (classCourseId == null) return "Entire class";
  const classCourse = courses.find((course) => course.id === classCourseId);
  return classCourse ? formatCourseTitle(classCourse.course) : "Course-specific";
}

export function canCreateContent(items, membership) {
  // The API has no collection-level can_manage. Only an empty collection needs
  // the existing membership UI hint; every existing item's flag is authoritative.
  return items.length > 0
    ? items.some((item) => item.can_manage === true)
    : isRepresentative(membership);
}

export function parseContentError(error) {
  const status = error.response?.status;
  const messages = {
    401: "Your session expired. Please log in again.",
    403: "You cannot perform this action. Representative access may be required.",
    404: "This content is unavailable or could not be found.",
    413: "The selected PDF is too large. The configured upload limit is 10 MB.",
  };
  if (messages[status]) return { message: messages[status], items: [] };
  if (status >= 500) {
    return { message: "ClassFlow is temporarily unavailable. Please try again.", items: [] };
  }
  return parseApiError(error);
}

export function validateResourceFile(file) {
  if (!file) return "Select a PDF file.";
  if (!/\.pdf$/i.test(file.name) || (file.type && file.type !== "application/pdf")) {
    return "Select a PDF file with a .pdf extension and PDF file type.";
  }
  // The server validates the actual bytes, size, and PDF contents.
  return null;
}
