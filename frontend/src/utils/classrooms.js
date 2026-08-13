export function formatClassTitle(classroom) {
  if (!classroom) return "Class";
  return `${classroom.name} - Semester ${classroom.semester} - Section ${classroom.section}`;
}

export function isRepresentative(membership) {
  return membership?.role === "representative" && membership?.status === "approved";
}

export function isApproved(membership) {
  return membership?.status === "approved";
}
