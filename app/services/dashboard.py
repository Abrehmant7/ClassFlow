from datetime import UTC, datetime

from app.core.config import settings
from app.repositories.dashboard import DashboardRepository
from app.schemas.dashboard import (
    DashboardAnnouncement,
    DashboardMembershipRequest,
    DashboardResponse,
    DashboardTaskSummary,
)
from app.services.feed import FeedService
from app.services.notification import NotificationService


class DashboardService:
    def __init__(
        self,
        repository: DashboardRepository,
        feed_service: FeedService,
        notification_service: NotificationService,
    ) -> None:
        self.repository = repository
        self.feed_service = feed_service
        self.notification_service = notification_service

    async def get_dashboard(
        self,
        user_id: int,
        timezone_name: str,
        *,
        now_utc: datetime | None = None,
    ) -> DashboardResponse:
        now_utc = now_utc or datetime.now(UTC)
        limit = settings.DASHBOARD_LIST_LIMIT
        summary = await self.feed_service.get_summary(user_id, timezone_name, now_utc=now_utc)

        task_lists = []
        for due in ("today", "week", "overdue"):
            task_lists.append(await self.feed_service.get_personal_feed(
                user_id=user_id,
                view="active",
                visibility="all",
                classroom_id=None,
                class_course_id=None,
                task_type=None,
                priority=None,
                due=due,
                search=None,
                timezone_name=timezone_name,
                page=1,
                page_size=limit,
                now_utc=now_utc,
            ))

        announcements = await self.repository.list_recent_announcements(user_id, limit)
        unread = await self.notification_service.count_unread(user_id)
        notifications = await self.notification_service.list_notifications(
            user_id,
            page=1,
            page_size=limit,
        )
        pending = await self.repository.list_pending_membership_requests(user_id, limit)

        return DashboardResponse(
            task_summary=DashboardTaskSummary(
                due_today=summary.due_today,
                upcoming=summary.upcoming_seven_days,
                overdue=summary.overdue,
            ),
            tasks_due_today=task_lists[0].items,
            upcoming_tasks=task_lists[1].items,
            overdue_tasks=task_lists[2].items,
            recent_announcements=[
                DashboardAnnouncement(
                    id=announcement.id,
                    title=announcement.title,
                    body=announcement.body,
                    classroom_id=announcement.classroom_id,
                    class_course_id=announcement.class_course_id,
                    created_at=announcement.created_at,
                    action_url=f"/classes/{announcement.classroom_id}?tab=announcements",
                )
                for announcement in announcements
            ],
            unread_notification_count=unread.unread_count,
            recent_notifications=notifications.items,
            pending_membership_request_count=pending.total,
            pending_membership_requests=[
                DashboardMembershipRequest(
                    id=membership.id,
                    classroom_id=membership.classroom_id,
                    classroom_name=membership.classroom.name,
                    requested_at=membership.requested_at,
                    user=membership.user,
                    action_url=f"/classes/{membership.classroom_id}/members",
                )
                for membership in pending.items
            ],
        )
