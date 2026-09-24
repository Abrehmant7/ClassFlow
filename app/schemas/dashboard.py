from datetime import datetime

from pydantic import BaseModel, Field

from app.schemas.classroom import MembershipUserRead
from app.schemas.feed import FeedTaskItem
from app.schemas.notification import NotificationRead


class DashboardTaskSummary(BaseModel):
    due_today: int = Field(ge=0)
    upcoming: int = Field(ge=0)
    overdue: int = Field(ge=0)


class DashboardAnnouncement(BaseModel):
    id: int
    title: str
    body: str
    classroom_id: int
    class_course_id: int | None
    created_at: datetime
    action_url: str


class DashboardMembershipRequest(BaseModel):
    id: int
    classroom_id: int
    classroom_name: str
    requested_at: datetime
    user: MembershipUserRead
    action_url: str


class DashboardResponse(BaseModel):
    task_summary: DashboardTaskSummary
    tasks_due_today: list[FeedTaskItem]
    upcoming_tasks: list[FeedTaskItem]
    overdue_tasks: list[FeedTaskItem]
    recent_announcements: list[DashboardAnnouncement]
    unread_notification_count: int = Field(ge=0)
    recent_notifications: list[NotificationRead]
    pending_membership_request_count: int = Field(ge=0)
    pending_membership_requests: list[DashboardMembershipRequest]
