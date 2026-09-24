from datetime import datetime, timedelta, timezone

import pytest
from sqlalchemy import func, select

from app.core.exceptions import ClassFlowError
from app.core.security import create_access_token
from app.models.classroom import Classroom
from app.models.notification import (
    NOTIFICATION_ANNOUNCEMENT_POSTED,
    NOTIFICATION_MEMBERSHIP_APPROVED,
    NOTIFICATION_MEMBERSHIP_REJECTED,
    NOTIFICATION_MEMBERSHIP_REQUEST,
    NOTIFICATION_TASK_CREATED,
    NOTIFICATION_TASK_UPDATED,
    Notification,
)
from app.models.reminder import REMINDER_PENDING, Reminder
from app.models.resource import RAG_SOURCE_TASK, RagChunk
from app.models.task import Task
from app.repositories.classroom import ClassroomRepository
from app.repositories.course import ClassCourseRepository, CourseRegistrationRepository
from app.repositories.membership import ClassMembershipRepository
from app.repositories.notification import NotificationRepository
from app.repositories.task import TaskAttachmentRepository, TaskProgressRepository, TaskRepository
from app.schemas.announcement import AnnouncementCreate
from app.schemas.classroom import ClassJoinRequest
from app.schemas.task import TaskCreate, TaskUpdate
from app.services.announcement import AnnouncementService
from app.services.classroom import ClassroomService
from app.services.notification import NotificationService
from app.services.reminder import ReminderService
from app.services.task import TaskService


@pytest.fixture
def anyio_backend():
    return "asyncio"


def notification_service(env) -> NotificationService:
    return NotificationService(env.session)


def reminder_service(env, notifications: NotificationService) -> ReminderService:
    return ReminderService(env.session, notification_service=notifications)


def task_service(env, notifications: NotificationService, reminders: ReminderService) -> TaskService:
    return TaskService(
        task_repository=TaskRepository(env.session),
        progress_repository=TaskProgressRepository(env.session),
        attachment_repository=TaskAttachmentRepository(env.session),
        membership_repository=ClassMembershipRepository(env.session),
        class_course_repository=ClassCourseRepository(env.session),
        registration_repository=CourseRegistrationRepository(env.session),
        rag_service=env.rag,
        notification_service=notifications,
        reminder_service=reminders,
    )


async def rows(env, event_type: str) -> list[Notification]:
    return list((await env.session.scalars(
        select(Notification)
        .where(Notification.event_type == event_type)
        .order_by(Notification.id.asc())
    )).all())


@pytest.mark.anyio
async def test_course_task_and_announcement_notify_only_authorized_non_actor_users(env):
    notifications = notification_service(env)
    reminders = reminder_service(env, notifications)
    tasks = task_service(env, notifications, reminders)
    deadline = datetime.now(timezone.utc) + timedelta(days=2)

    created = await tasks.create_class_task(
        env.classroom_id,
        TaskCreate(
            title="Unique course assignment",
            visibility="shared",
            class_course_id=env.course_id,
            deadline=deadline,
        ),
        env.users["rep"],
    )
    created_notifications = await rows(env, NOTIFICATION_TASK_CREATED)
    assert [row.recipient_user_id for row in created_notifications] == [env.users["student"]]
    assert all(row.actor_user_id == env.users["rep"] for row in created_notifications)
    assert await env.session.scalar(select(func.count()).select_from(Reminder).where(
        Reminder.task_id == created.id,
        Reminder.recipient_user_id == env.users["student"],
        Reminder.status == REMINDER_PENDING,
    )) == 1

    await tasks.update_task(created.id, TaskUpdate(title="Updated course assignment"), env.users["rep"])
    assert [row.recipient_user_id for row in await rows(env, NOTIFICATION_TASK_UPDATED)] == [env.users["student"]]
    before_empty_patch = len(await rows(env, NOTIFICATION_TASK_UPDATED))
    await tasks.update_task(created.id, TaskUpdate(), env.users["rep"])
    assert len(await rows(env, NOTIFICATION_TASK_UPDATED)) == before_empty_patch

    announcements = AnnouncementService(
        env.session,
        rag_service=env.rag,
        notification_service=notifications,
    )
    announcement = await announcements.create_announcement(
        env.classroom_id,
        AnnouncementCreate(
            title="Course announcement",
            body="Registered students and representatives only",
            class_course_id=env.course_id,
        ),
        env.users["rep"],
    )
    announcement_notifications = await rows(env, NOTIFICATION_ANNOUNCEMENT_POSTED)
    assert [row.recipient_user_id for row in announcement_notifications] == [env.users["student"]]
    assert announcement_notifications[0].source_id == announcement.id


@pytest.mark.anyio
async def test_membership_request_approval_and_rejection_events(env):
    notifications = notification_service(env)
    reminders = reminder_service(env, notifications)
    service = ClassroomService(
        ClassroomRepository(env.session),
        ClassMembershipRepository(env.session),
        notification_service=notifications,
        reminder_service=reminders,
    )
    classroom = await env.session.get(Classroom, env.classroom_id)
    classroom.join_code = "M7TEST01"
    await env.session.flush()

    outsider_request = await service.join_classroom(
        env.classroom_id,
        env.users["outsider"],
        ClassJoinRequest(join_code="M7TEST01"),
    )
    request_rows = await rows(env, NOTIFICATION_MEMBERSHIP_REQUEST)
    assert request_rows[-1].recipient_user_id == env.users["rep"]
    assert request_rows[-1].actor_user_id == env.users["outsider"]

    await service.approve_membership(outsider_request.id, env.users["rep"])
    approved_rows = await rows(env, NOTIFICATION_MEMBERSHIP_APPROVED)
    assert approved_rows[-1].recipient_user_id == env.users["outsider"]
    assert approved_rows[-1].action_url == f"/classes/{env.classroom_id}"

    removed_request = await service.join_classroom(
        env.classroom_id,
        env.users["removed"],
        ClassJoinRequest(join_code="M7TEST01"),
    )
    await service.reject_membership(removed_request.id, env.users["rep"])
    rejected_rows = await rows(env, NOTIFICATION_MEMBERSHIP_REJECTED)
    assert rejected_rows[-1].recipient_user_id == env.users["removed"]


@pytest.mark.anyio
async def test_notification_reads_and_mutations_are_recipient_scoped(env):
    repository = NotificationRepository(env.session)
    created = (await repository.create_many([{
        "recipient_user_id": env.users["student"],
        "actor_user_id": env.users["rep"],
        "classroom_id": env.classroom_id,
        "event_type": NOTIFICATION_TASK_CREATED,
        "title": "Scoped",
        "message": "Only the recipient can change this.",
        "source_type": "task",
        "source_id": 123,
        "action_url": "/tasks/123",
    }]))[0]
    await env.session.commit()
    service = NotificationService(env.session, repository=repository)

    listed = await service.list_notifications(env.users["student"])
    assert created.id in {item.id for item in listed.items}
    assert "dedupe_key" not in listed.items[0].model_dump()
    assert (await service.count_unread(env.users["student"])).unread_count >= 1

    with pytest.raises(ClassFlowError) as caught:
        await service.mark_read(created.id, env.users["outsider"])
    assert caught.value.status_code == 404

    read = await service.mark_read(created.id, env.users["student"])
    assert read.is_read is True and read.read_at is not None
    unread = await service.mark_unread(created.id, env.users["student"])
    assert unread.is_read is False and unread.read_at is None
    await service.mark_all_read(env.users["student"])
    assert (await service.count_unread(env.users["student"])).unread_count == 0


@pytest.mark.anyio
async def test_task_notification_failure_rolls_back_task_rag_chunks_and_reminders(env, monkeypatch):
    notifications = notification_service(env)
    reminders = reminder_service(env, notifications)
    tasks = task_service(env, notifications, reminders)

    async def fail_notification_insert(_rows):
        raise RuntimeError("simulated notification insert failure")

    monkeypatch.setattr(notifications.repository, "create_many", fail_notification_insert)
    with pytest.raises(RuntimeError):
        await tasks.create_class_task(
            env.classroom_id,
            TaskCreate(
                title="Atomic task creation",
                visibility="shared",
                deadline=datetime.now(timezone.utc) + timedelta(days=2),
            ),
            env.users["rep"],
        )

    assert await env.session.scalar(select(func.count()).select_from(Task).where(
        Task.title == "Atomic task creation",
    )) == 0
    assert await env.session.scalar(select(func.count()).select_from(RagChunk).where(
        RagChunk.source_type == RAG_SOURCE_TASK,
        RagChunk.classroom_id == env.classroom_id,
    )) == 0
    assert await env.session.scalar(select(func.count()).select_from(Reminder)) == 0


def auth_headers(user_id: int) -> dict[str, str]:
    return {"Authorization": f"Bearer {create_access_token(str(user_id))}"}


@pytest.mark.anyio
async def test_notification_api_is_recipient_scoped_and_supports_read_workflow(env, api):
    repository = NotificationRepository(env.session)
    student_notification, outsider_notification = await repository.create_many([
        {
            "recipient_user_id": env.users["student"],
            "actor_user_id": env.users["rep"],
            "classroom_id": env.classroom_id,
            "event_type": NOTIFICATION_TASK_CREATED,
            "title": "Student notification",
            "message": "Visible to the student only.",
            "source_type": "task",
            "source_id": 201,
            "action_url": "/tasks/201",
        },
        {
            "recipient_user_id": env.users["outsider"],
            "actor_user_id": env.users["rep"],
            "classroom_id": env.classroom_id,
            "event_type": NOTIFICATION_TASK_CREATED,
            "title": "Outsider notification",
            "message": "Visible to the outsider only.",
            "source_type": "task",
            "source_id": 202,
            "action_url": "/tasks/202",
        },
    ])
    await env.session.commit()

    student_headers = auth_headers(env.users["student"])
    listed = await api.get("/api/v1/notifications", headers=student_headers)
    assert listed.status_code == 200
    assert student_notification.id in {item["id"] for item in listed.json()["items"]}
    assert outsider_notification.id not in {item["id"] for item in listed.json()["items"]}
    assert all("dedupe_key" not in item for item in listed.json()["items"])

    forbidden = await api.patch(
        f"/api/v1/notifications/{outsider_notification.id}/read",
        headers=student_headers,
    )
    assert forbidden.status_code == 404

    read = await api.patch(
        f"/api/v1/notifications/{student_notification.id}/read",
        headers=student_headers,
    )
    assert read.status_code == 200 and read.json()["is_read"] is True
    unread = await api.patch(
        f"/api/v1/notifications/{student_notification.id}/unread",
        headers=student_headers,
    )
    assert unread.status_code == 200 and unread.json()["is_read"] is False
    mark_all = await api.post("/api/v1/notifications/read-all", headers=student_headers)
    assert mark_all.status_code == 200 and mark_all.json()["updated_count"] >= 1
    count = await api.get("/api/v1/notifications/unread-count", headers=student_headers)
    assert count.json() == {"unread_count": 0}
