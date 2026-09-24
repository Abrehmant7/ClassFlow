from datetime import datetime, timezone

import pytest

from app.core.exceptions import ClassFlowError
from app.models.announcement import Announcement
from app.models.notification import NOTIFICATION_TASK_CREATED
from app.models.task import Task, TaskProgress
from app.repositories.dashboard import DashboardRepository
from app.repositories.feed import FeedRepository
from app.repositories.membership import ClassMembershipRepository
from app.repositories.notification import NotificationRepository
from app.services.dashboard import DashboardService
from app.services.feed import FeedService
from app.services.notification import NotificationService


@pytest.fixture
def anyio_backend():
    return "asyncio"


def dashboard_service(env) -> DashboardService:
    return DashboardService(
        DashboardRepository(env.session),
        FeedService(FeedRepository(env.session), ClassMembershipRepository(env.session)),
        NotificationService(env.session),
    )


def shared_task(env, title: str, deadline: datetime) -> Task:
    return Task(
        classroom_id=env.classroom_id,
        created_by_user_id=env.users["rep"],
        title=title,
        task_type="assignment",
        visibility="shared",
        priority="medium",
        status="active",
        deadline=deadline,
    )


@pytest.mark.anyio
async def test_dashboard_reuses_feed_boundaries_and_excludes_completed_tasks(env):
    fixed_now = datetime(2026, 9, 24, 12, 0, tzinfo=timezone.utc)
    overdue = shared_task(env, "Dashboard overdue", datetime(2026, 9, 24, 10, 0, tzinfo=timezone.utc))
    due_today = shared_task(env, "Dashboard today", datetime(2026, 9, 24, 18, 0, tzinfo=timezone.utc))
    upcoming = shared_task(env, "Dashboard upcoming", datetime(2026, 9, 25, 12, 0, tzinfo=timezone.utc))
    completed = shared_task(env, "Dashboard completed", datetime(2026, 9, 24, 17, 0, tzinfo=timezone.utc))
    env.session.add_all([overdue, due_today, upcoming, completed])
    await env.session.flush()
    membership = await ClassMembershipRepository(env.session).get_by_user_and_class(
        env.users["student"], env.classroom_id,
    )
    env.session.add(TaskProgress(
        task_id=completed.id,
        membership_id=membership.id,
        status="completed",
        completed_at=fixed_now,
    ))
    await env.session.commit()

    dashboard = await dashboard_service(env).get_dashboard(
        env.users["student"],
        "Asia/Karachi",
        now_utc=fixed_now,
    )
    # The feed defines "due today" by the local calendar day, so a task that
    # became overdue earlier today appears in both the today and overdue views.
    assert dashboard.task_summary.model_dump() == {"due_today": 2, "upcoming": 1, "overdue": 1}
    assert {task.id for task in dashboard.tasks_due_today} == {overdue.id, due_today.id}
    assert [task.id for task in dashboard.upcoming_tasks] == [upcoming.id]
    assert [task.id for task in dashboard.overdue_tasks] == [overdue.id]
    active_ids = {
        task.id
        for section in (dashboard.tasks_due_today, dashboard.upcoming_tasks, dashboard.overdue_tasks)
        for task in section
    }
    assert completed.id not in active_ids


@pytest.mark.anyio
async def test_dashboard_scopes_announcements_notifications_and_pending_requests(env):
    env.session.add_all([
        Announcement(
            classroom_id=env.classroom_id,
            created_by_user_id=env.users["rep"],
            title="Class dashboard announcement",
            body="Visible to approved class members.",
        ),
        Announcement(
            classroom_id=env.classroom_id,
            class_course_id=env.course_id,
            created_by_user_id=env.users["rep"],
            title="Course dashboard announcement",
            body="Visible only with course access.",
        ),
    ])
    await NotificationRepository(env.session).create_many([
        {
            "recipient_user_id": env.users["student"],
            "actor_user_id": env.users["rep"],
            "classroom_id": env.classroom_id,
            "event_type": NOTIFICATION_TASK_CREATED,
            "title": "Student dashboard notification",
            "message": "Student only.",
            "source_type": "task",
            "source_id": 301,
            "action_url": "/tasks/301",
        },
        {
            "recipient_user_id": env.users["outsider"],
            "actor_user_id": env.users["rep"],
            "classroom_id": env.classroom_id,
            "event_type": NOTIFICATION_TASK_CREATED,
            "title": "Outsider dashboard notification",
            "message": "Outsider only.",
            "source_type": "task",
            "source_id": 302,
            "action_url": "/tasks/302",
        },
    ])
    await env.session.commit()

    service = dashboard_service(env)
    student = await service.get_dashboard(env.users["student"], "UTC")
    assert {item.title for item in student.recent_announcements} == {
        "Class dashboard announcement",
        "Course dashboard announcement",
    }
    assert student.unread_notification_count == 1
    assert [item.title for item in student.recent_notifications] == ["Student dashboard notification"]
    assert student.pending_membership_request_count == 0
    assert student.pending_membership_requests == []

    unregistered = await service.get_dashboard(env.users["unregistered"], "UTC")
    assert {item.title for item in unregistered.recent_announcements} == {"Class dashboard announcement"}

    representative = await service.get_dashboard(env.users["rep"], "UTC")
    assert representative.pending_membership_request_count == 1
    assert representative.pending_membership_requests[0].user.id == env.users["pending"]


@pytest.mark.anyio
async def test_dashboard_rejects_unknown_timezone(env):
    with pytest.raises(ClassFlowError) as caught:
        await dashboard_service(env).get_dashboard(env.users["student"], "Mars/Olympus_Mons")
    assert getattr(caught.value, "status_code", None) == 422
