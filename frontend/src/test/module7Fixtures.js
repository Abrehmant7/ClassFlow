export const notification = {
  id: 1, event_type: "task_created", title: "New task", message: "A task was posted.",
  classroom_id: 4, source_type: "task", source_id: 20, action_url: "/tasks/20",
  is_read: false, read_at: null, created_at: "2026-09-24T12:00:00Z",
};

export const feedTask = {
  id: 20, title: "Database assignment", description: "Complete exercises.",
  visibility: "shared", task_type: "assignment", priority: "high", task_status: "active",
  my_completion_status: "pending", deadline: "2026-09-28T12:00:00Z", due_group: "upcoming",
  classroom: { id: 4, name: "Computer Science" }, course: null, attachment_count: 0,
  permissions: { can_edit: false, can_delete: false, can_manage: false, can_update_progress: true },
};

export const dashboard = {
  task_summary: { due_today: 2, upcoming: 5, overdue: 1 },
  tasks_due_today: [feedTask], upcoming_tasks: [{ ...feedTask, id: 21, title: "Lab writeup" }],
  overdue_tasks: [{ ...feedTask, id: 22, title: "Old quiz", task_status: "active" }],
  recent_announcements: [{ id: 8, title: "Class meeting", body: "Meet in room 3.", classroom_id: 4,
    class_course_id: null, created_at: "2026-09-24T12:00:00Z", action_url: "/classes/4?tab=announcements" }],
  unread_notification_count: 3,
  recent_notifications: [notification],
  pending_membership_request_count: 2,
  pending_membership_requests: [{ id: 30, classroom_id: 4, classroom_name: "Computer Science",
    requested_at: "2026-09-24T12:00:00Z", user: { id: 7, first_name: "Ada", username: "ada" },
    action_url: "/classes/4/members" }],
};

export const searchResults = {
  items: [
    { entity_type: "task", id: 20, title: "Database assignment", preview: "Complete exercises.",
      classroom_id: 4, class_course_id: 12, date: "2026-09-28T12:00:00Z", task_type: "assignment",
      priority: "high", status: "active", action_url: "/tasks/20" },
    { entity_type: "announcement", id: 8, title: "Class meeting", preview: "Meet in room 3.",
      classroom_id: 4, class_course_id: null, date: "2026-09-24T12:00:00Z",
      task_type: null, priority: null, status: null, action_url: "/classes/4?tab=announcements" },
    { entity_type: "resource", id: 9, title: "Course notes", preview: "Week one PDF.",
      classroom_id: 4, class_course_id: 12, date: "2026-09-24T12:00:00Z",
      task_type: null, priority: null, status: null, action_url: "/classes/4?tab=resources&resource=9" },
  ], total: 3, page: 1, page_size: 20, total_pages: 1,
};

export const classroom = { id: 4, name: "Computer Science", is_active: true,
  membership: { role: "representative", status: "approved" } };
export const classCourse = { id: 12, is_active: true, course: { code: "CS201", name: "Data Structures" } };

export function deferred() {
  let resolve;
  let reject;
  const promise = new Promise((yes, no) => { resolve = yes; reject = no; });
  return { promise, resolve, reject };
}

export function apiError(status, detail = "Internal detail") {
  return { response: { status, data: { detail } } };
}
