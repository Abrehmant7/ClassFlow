from datetime import datetime, timedelta, timezone
from uuid import uuid4

import pytest

from app.core.security import create_access_token
from app.repositories.course import ClassCourseRepository, CourseRegistrationRepository
from app.repositories.membership import ClassMembershipRepository
from app.repositories.task import TaskAttachmentRepository, TaskProgressRepository, TaskRepository
from app.schemas.task import TaskCreate
from app.services.notification import NotificationService
from app.services.reminder import ReminderService
from app.services.task import TaskService


@pytest.fixture
def anyio_backend():
    return "asyncio"


def headers(user_id: int) -> dict[str, str]:
    return {"Authorization": f"Bearer {create_access_token(str(user_id))}"}


def task_service(env) -> TaskService:
    notifications = NotificationService(env.session)
    return TaskService(
        task_repository=TaskRepository(env.session),
        progress_repository=TaskProgressRepository(env.session),
        attachment_repository=TaskAttachmentRepository(env.session),
        membership_repository=ClassMembershipRepository(env.session),
        class_course_repository=ClassCourseRepository(env.session),
        registration_repository=CourseRegistrationRepository(env.session),
        rag_service=env.rag,
        notification_service=notifications,
        reminder_service=ReminderService(env.session, notification_service=notifications),
    )


@pytest.mark.anyio
async def test_shared_course_task_is_consistent_across_feed_notifications_dashboard_and_search(env, api):
    marker = uuid4().hex[:10]
    title = f"Checkpoint {marker} task"
    student_headers = headers(env.users["student"])
    unregistered_headers = headers(env.users["unregistered"])

    before = await api.get("/api/v1/dashboard", params={"timezone": "UTC"}, headers=student_headers)
    assert before.status_code == 200
    before_upcoming = before.json()["task_summary"]["upcoming"]

    task = await task_service(env).create_class_task(
        env.classroom_id,
        TaskCreate(
            title=title,
            description="One task must have one authorization result everywhere.",
            visibility="shared",
            class_course_id=env.course_id,
            deadline=datetime.now(timezone.utc) + timedelta(days=2),
        ),
        env.users["rep"],
    )

    feed = await api.get("/api/v1/feed", headers=student_headers)
    assert feed.status_code == 200
    assert task.id in {item["id"] for item in feed.json()["items"]}

    notifications = await api.get("/api/v1/notifications", headers=student_headers)
    assert notifications.status_code == 200
    assert any(
        item["event_type"] == "task_created" and item["source_id"] == task.id
        for item in notifications.json()["items"]
    )

    dashboard = await api.get("/api/v1/dashboard", params={"timezone": "UTC"}, headers=student_headers)
    assert dashboard.status_code == 200
    assert dashboard.json()["task_summary"]["upcoming"] == before_upcoming + 1
    assert task.id in {item["id"] for item in dashboard.json()["upcoming_tasks"]}

    search = await api.get("/api/v1/search", params={"q": title}, headers=student_headers)
    assert search.status_code == 200
    assert task.id in {item["id"] for item in search.json()["items"] if item["entity_type"] == "task"}

    unregistered_feed = await api.get("/api/v1/feed", headers=unregistered_headers)
    assert task.id not in {item["id"] for item in unregistered_feed.json()["items"]}
    unregistered_notifications = await api.get("/api/v1/notifications", headers=unregistered_headers)
    assert not any(item["source_id"] == task.id for item in unregistered_notifications.json()["items"])
    unregistered_dashboard = await api.get("/api/v1/dashboard", params={"timezone": "UTC"}, headers=unregistered_headers)
    dashboard_task_ids = {
        item["id"]
        for key in ("tasks_due_today", "upcoming_tasks", "overdue_tasks")
        for item in unregistered_dashboard.json()[key]
    }
    assert task.id not in dashboard_task_ids
    unregistered_search = await api.get("/api/v1/search", params={"q": title}, headers=unregistered_headers)
    assert unregistered_search.status_code == 200 and unregistered_search.json()["items"] == []
