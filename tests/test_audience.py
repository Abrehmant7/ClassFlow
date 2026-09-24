from datetime import datetime, timedelta, timezone

import pytest
from sqlalchemy.dialects import postgresql

from app.core.config import settings
from app.models.classroom import ClassMembership
from app.models.notification import NOTIFICATION_TASK_CREATED, Notification
from app.models.reminder import REMINDER_PENDING, Reminder
from app.models.task import (
    TASK_PROGRESS_COMPLETED,
    TASK_STATUS_ACTIVE,
    TASK_VISIBILITY_PERSONAL,
    TASK_VISIBILITY_SHARED,
    Task,
    TaskProgress,
)
from app.repositories.audience import AudienceRepository, task_access_condition
from app.repositories.feed import FeedRepository


@pytest.fixture
def anyio_backend():
    return "asyncio"


def test_module7_model_constraints_indexes_and_defaults():
    notification_constraints = {constraint.name for constraint in Notification.__table__.constraints}
    notification_indexes = {index.name for index in Notification.__table__.indexes}
    reminder_constraints = {constraint.name for constraint in Reminder.__table__.constraints}
    reminder_indexes = {index.name for index in Reminder.__table__.indexes}

    assert "ck_notifications_event_type" in notification_constraints
    assert "ix_notifications_recipient_read_created" in notification_indexes
    assert "ix_notifications_dedupe_key" in notification_indexes
    assert "ck_reminders_status" in reminder_constraints
    assert "uq_reminders_task_recipient_remind_at" in reminder_constraints
    assert "ix_reminders_status_remind_at" in reminder_indexes
    assert settings.REMINDER_LEAD_MINUTES == 1440
    assert settings.REMINDER_BATCH_SIZE == 100
    assert settings.DASHBOARD_LIST_LIMIT == 5


def test_shared_task_access_condition_contains_representative_and_registration_paths():
    compiled = str(
        task_access_condition(user_id=42).compile(
            dialect=postgresql.dialect(),
            compile_kwargs={"literal_binds": True},
        )
    )

    assert "class_memberships" in compiled
    assert "classrooms_1.is_active IS true" in compiled
    assert "class_courses" in compiled
    assert "class_courses.is_active IS true" in compiled
    assert "course_registrations_1.is_active IS true" in compiled
    assert "class_memberships" in compiled and "role = 'representative'" in compiled


@pytest.mark.anyio
async def test_audiences_and_feed_share_course_representative_access(env):
    audience = AudienceRepository(env.session)
    expected_class = {
        env.users["rep"],
        env.users["student"],
        env.users["unregistered"],
    }
    assert set(await audience.list_class_recipients(env.classroom_id)) == expected_class
    assert await audience.list_representatives(env.classroom_id) == [env.users["rep"]]
    assert set(await audience.list_course_recipients(env.classroom_id, env.course_id)) == {
        env.users["rep"],
        env.users["student"],
    }
    assert await audience.list_course_recipients(
        env.classroom_id,
        env.course_id,
        exclude_user_id=env.users["rep"],
    ) == [env.users["student"]]

    task = Task(
        classroom_id=env.classroom_id,
        class_course_id=env.course_id,
        created_by_user_id=env.users["rep"],
        title="Module 7 audience task",
        description="Course audience",
        task_type="assignment",
        visibility=TASK_VISIBILITY_SHARED,
        priority="medium",
        status=TASK_STATUS_ACTIVE,
    )
    env.session.add(task)
    await env.session.flush()

    assert set(await audience.list_task_recipients(task)) == {
        env.users["rep"],
        env.users["student"],
    }
    assert await audience.list_task_recipients(
        task,
        students_only=True,
        incomplete_only=True,
    ) == [env.users["student"]]

    student_membership_id = await env.session.scalar(
        ClassMembership.__table__.select()
        .with_only_columns(ClassMembership.id)
        .where(
            ClassMembership.classroom_id == env.classroom_id,
            ClassMembership.user_id == env.users["student"],
        )
    )
    env.session.add(TaskProgress(
        task_id=task.id,
        membership_id=student_membership_id,
        status=TASK_PROGRESS_COMPLETED,
        completed_at=datetime.now(timezone.utc),
    ))
    await env.session.flush()
    assert await audience.list_task_recipients(
        task,
        students_only=True,
        incomplete_only=True,
    ) == []

    feed = FeedRepository(env.session)
    assert task.id in {item.id for item, _progress in (
        await feed.list_personal_feed(
            user_id=env.users["rep"],
            view="all",
            visibility="all",
            classroom_id=None,
            class_course_id=None,
            task_type=None,
            priority=None,
            due=None,
            search=None,
            now_utc=datetime.now(timezone.utc),
            today_start_utc=datetime.now(timezone.utc).replace(hour=0, minute=0, second=0, microsecond=0),
            today_end_utc=datetime.now(timezone.utc).replace(hour=0, minute=0, second=0, microsecond=0) + timedelta(days=1),
            week_end_utc=datetime.now(timezone.utc) + timedelta(days=7),
            page=1,
            page_size=20,
        )
    ).tasks}
    assert await feed.user_can_filter_class_course(env.users["rep"], env.course_id) is True

    personal = Task(
        id=999_999,
        created_by_user_id=env.users["outsider"],
        title="Personal",
        task_type="assignment",
        visibility=TASK_VISIBILITY_PERSONAL,
        priority="medium",
        status=TASK_STATUS_ACTIVE,
    )
    assert await audience.list_task_recipients(personal) == [env.users["outsider"]]

    now = datetime.now(timezone.utc)
    notification = Notification(
        recipient_user_id=env.users["student"],
        actor_user_id=env.users["rep"],
        classroom_id=env.classroom_id,
        event_type=NOTIFICATION_TASK_CREATED,
        title="New task",
        message=task.title,
        source_type="task",
        source_id=task.id,
        action_url=f"/tasks/{task.id}",
    )
    reminder = Reminder(
        task_id=task.id,
        recipient_user_id=env.users["student"],
        remind_at=now + timedelta(hours=1),
        status=REMINDER_PENDING,
        deadline_snapshot=now + timedelta(days=1),
    )
    env.session.add_all([notification, reminder])
    await env.session.flush()
    assert notification.id is not None
    assert reminder.id is not None
