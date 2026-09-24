export const classroom = {
  id: 1, name: "Computer Science", semester: 5, section: "A", is_active: true,
  membership: { role: "representative", status: "approved" },
};

export const courses = [
  { id: 11, is_active: true, course: { code: "CS201", name: "Data Structures" } },
  { id: 12, is_active: false, course: { code: "CS101", name: "Programming" } },
];

export const announcement = {
  id: 10, classroom_id: 1, class_course_id: null, created_by_user_id: 1,
  title: "Class meeting", body: "Meet in room 3.\nBring your notes.", is_pinned: false,
  created_at: "2026-09-20T09:00:00Z", updated_at: "2026-09-20T09:00:00Z", can_manage: true,
};

export const resource = {
  id: 20, classroom_id: 1, class_course_id: 11, uploaded_by_user_id: 1,
  title: "Week one notes", description: "Read before class.", file_name: "notes.pdf",
  content_type: "application/pdf", file_size: 2048, is_enabled: true,
  indexing_status: "indexed", indexing_error: null, indexed_at: "2026-09-20T09:01:00Z",
  created_at: "2026-09-20T09:00:00Z", updated_at: "2026-09-20T09:00:00Z", can_manage: true,
};

export function apiError(status, detail = "Backend message") {
  return { response: { status, data: { detail } } };
}

export function deferred() {
  let resolve;
  let reject;
  const promise = new Promise((yes, no) => { resolve = yes; reject = no; });
  return { promise, resolve, reject };
}
