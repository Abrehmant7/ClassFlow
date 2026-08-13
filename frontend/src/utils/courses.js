export function formatCourseTitle(course) {
  if (!course) return "Course";
  return `${course.code} - ${course.name}`;
}

export function normalizeCourseCode(code) {
  return code.trim().toUpperCase();
}

export function normalizeCourseName(name) {
  return name.trim().split(/\s+/).join(" ");
}

export function isSameCourseQuery(course, query) {
  const term = query.trim().toLowerCase();
  if (!term) return false;

  return (
    course.name.toLowerCase() === term ||
    course.code.toLowerCase() === term
  );
}
