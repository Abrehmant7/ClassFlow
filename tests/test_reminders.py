from datetime import datetime, timedelta, timezone

import pytest
from sqlalchemy import select

from app.models.notification import NOTIFICATION_DEADLINE_APPROACHING, Notification
from app.models.classroom import ClassMembership
from app.models.reminder import REMINDER_CANCELLED, REMINDER_PENDING, REMINDER_SENT, Reminder
from app.repositories.classroom import ClassroomRepository
from app.repositories.course import ClassCourseRepository, CourseRegistrationRepository
from app.repositories.membership import ClassMembershipRepository
from app.repositories.task import TaskAttachmentRepository, TaskProgressRepository, TaskRepository
from app.schemas.task import TaskCreate, TaskProgressUpdate, TaskUpdate
from app.services.course import CourseRegistrationService
from app.services.classroom import ClassroomService
from app.services.notification import NotificationService
from app.services.reminder import ReminderService
from app.services.task import TaskService


@pytest.fixture
def anyio_backend():
    return "asyncio"


def services(env):
    notifications = NotificationService(env.session)
    reminders = ReminderService(env.session, notification_service=notifications)
    tasks = TaskService(
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
    return notifications, reminders, tasks


async def task_reminders(env, task_id: int) -> list[Reminder]:
    return list((await env.session.scalars(
        select(Reminder).where(Reminder.task_id == task_id).order_by(Reminder.id.asc())
    )).all())


@pytest.mark.anyio
async def test_deadline_changes_reschedule_and_task_cancellation_cancels(env):
    _notifications, _reminders, tasks = services(env)
    original_deadline = datetime.now(timezone.utc) + timedelta(days=3)
    created = await tasks.create_class_task(
        env.classroom_id,
        TaskCreate(
            title="Rescheduled course task",
            visibility="shared",
            class_course_id=env.course_id,
            deadline=original_deadline,
        ),
        env.users["rep"],
    )
    initial = await task_reminders(env, created.id)
    assert len(initial) == 1
    assert initial[0].status == REMINDER_PENDING
    assert initial[0].deadline_snapshot == original_deadline

    new_deadline = original_deadline + timedelta(days=2)
    await tasks.update_task(created.id, TaskUpdate(deadline=new_deadline), env.users["rep"])
    rescheduled = await task_reminders(env, created.id)
    assert len(rescheduled) == 2
    assert [row.status for row in rescheduled].count(REMINDER_CANCELLED) == 1
    assert [row.status for row in rescheduled].count(REMINDER_PENDING) == 1
    assert next(row for row in rescheduled if row.status == REMINDER_PENDING).deadline_snapshot == new_deadline

    await tasks.update_task(created.id, TaskUpdate(status="cancelled"), env.users["rep"])
    assert all(row.status == REMINDER_CANCELLED for row in await task_reminders(env, created.id))


@pytest.mark.anyio
async def test_progress_completion_cancels_and_pending_restores_student_reminder(env):
    _notifications, _reminders, tasks = services(env)
    created = await tasks.create_class_task(
        env.classroom_id,
        TaskCreate(
            title="Progress reminder task",
            visibility="shared",
            class_course_id=env.course_id,
            deadline=datetime.now(timezone.utc) + timedelta(days=2),
        ),
        env.users["rep"],
    )
    reminder = (await task_reminders(env, created.id))[0]
    assert reminder.recipient_user_id == env.users["student"]

    await tasks.update_progress(
        created.id,
        TaskProgressUpdate(status="completed"),
        env.users["student"],
    )
    assert (await task_reminders(env, created.id))[0].status == REMINDER_CANCELLED

    await tasks.update_progress(
        created.id,
        TaskProgressUpdate(status="pending"),
        env.users["student"],
    )
    restored = await task_reminders(env, created.id)
    assert len(restored) == 1
    assert restored[0].status == REMINDER_PENDING


@pytest.mark.anyio
async def test_course_registration_and_drop_synchronize_reminders(env):
    notifications, reminders, tasks = services(env)
    created = await tasks.create_class_task(
        env.classroom_id,
        TaskCreate(
            title="Optional course task",
            visibility="shared",
            class_course_id=env.course_id,
            deadline=datetime.now(timezone.utc) + timedelta(days=2),
        ),
        env.users["rep"],
    )
    assert env.users["unregistered"] not in {
        row.recipient_user_id for row in await task_reminders(env, created.id)
    }

    registrations = CourseRegistrationService(
        ClassMembershipRepository(env.session),
        ClassCourseRepository(env.session),
        CourseRegistrationRepository(env.session),
        reminder_service=reminders,
    )
    await registrations.register_optional_course(env.course_id, env.users["unregistered"])
    reminder = next(
        row for row in await task_reminders(env, created.id)
        if row.recipient_user_id == env.users["unregistered"]
    )
    assert reminder.status == REMINDER_PENDING
    reminder_id = reminder.id

    await registrations.drop_course(env.course_id, env.users["unregistered"])
    env.session.expire_all()
    reminder = await env.session.get(Reminder, reminder_id)
    assert reminder.status == REMINDER_CANCELLED


@pytest.mark.anyio
async def test_worker_sends_once_and_marks_stale_or_unauthorized_reminders_cancelled(env):
    _notifications, reminders, tasks = services(env)
    created = await tasks.create_class_task(
        env.classroom_id,
        TaskCreate(
            title="Worker deadline task",
            visibility="shared",
            class_course_id=env.course_id,
            deadline=datetime.now(timezone.utc) + timedelta(days=2),
        ),
        env.users["rep"],
    )
    reminder = (await task_reminders(env, created.id))[0]
    reminder_id = reminder.id
    process_at = reminder.remind_at + timedelta(seconds=1)
    assert process_at < reminder.deadline_snapshot

    assert await reminders.process_due_reminders(process_at) == 1
    assert await reminders.process_due_reminders(process_at) == 0
    env.session.expire_all()
    saved = await env.session.get(Reminder, reminder_id)
    assert saved.status == REMINDER_SENT
    deadline_notifications = list((await env.session.scalars(select(Notification).where(
        Notification.event_type == NOTIFICATION_DEADLINE_APPROACHING,
        Notification.source_id == created.id,
        Notification.recipient_user_id == env.users["student"],
    ))).all())
    assert len(deadline_notifications) == 1
    assert deadline_notifications[0].dedupe_key is not None


@pytest.mark.anyio
async def test_personal_task_reminder_belongs_only_to_owner(env):
    _notifications, _reminders, tasks = services(env)
    created = await tasks.create_personal_task(
        TaskCreate(
            title="Personal deadline",
            visibility="personal",
            deadline=datetime.now(timezone.utc) + timedelta(days=2),
        ),
        env.users["student"],
    )
    rows = await task_reminders(env, created.id)
    assert len(rows) == 1
    assert rows[0].recipient_user_id == env.users["student"]

    without_deadline = await tasks.create_personal_task(
        TaskCreate(title="No reminder", visibility="personal"),
        env.users["student"],
    )
    assert await task_reminders(env, without_deadline.id) == []


@pytest.mark.anyio
async def test_membership_approval_and_removal_synchronize_class_reminders(env):
    notifications, reminders, tasks = services(env)
    created = await tasks.create_class_task(
        env.classroom_id,
        TaskCreate(
            title="Class-wide future task",
            visibility="shared",
            deadline=datetime.now(timezone.utc) + timedelta(days=2),
        ),
        env.users["rep"],
    )
    pending_membership_id = await env.session.scalar(
        select(ClassMembership.id).where(
            ClassMembership.classroom_id == env.classroom_id,
            ClassMembership.user_id == env.users["pending"],
        )
    )
    classroom_service = ClassroomService(
        ClassroomRepository(env.session),
        ClassMembershipRepository(env.session),
        notification_service=notifications,
        reminder_service=reminders,
    )
    await classroom_service.approve_membership(pending_membership_id, env.users["rep"])
    pending_user_reminder = next(
        row for row in await task_reminders(env, created.id)
        if row.recipient_user_id == env.users["pending"]
    )
    assert pending_user_reminder.status == REMINDER_PENDING
    reminder_id = pending_user_reminder.id

    await classroom_service.remove_membership(pending_membership_id, env.users["rep"])
    env.session.expire_all()
    assert (await env.session.get(Reminder, reminder_id)).status == REMINDER_CANCELLED
