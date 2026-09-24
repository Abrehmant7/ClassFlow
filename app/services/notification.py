from datetime import datetime, timezone

from fastapi import status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import ClassFlowError
from app.models.announcement import Announcement
from app.models.classroom import Classroom, ClassMembership
from app.models.notification import (
    NOTIFICATION_ANNOUNCEMENT_POSTED,
    NOTIFICATION_DEADLINE_APPROACHING,
    NOTIFICATION_MEMBERSHIP_APPROVED,
    NOTIFICATION_MEMBERSHIP_REJECTED,
    NOTIFICATION_MEMBERSHIP_REQUEST,
    NOTIFICATION_TASK_CREATED,
    NOTIFICATION_TASK_UPDATED,
    Notification,
)
from app.models.task import Task
from app.models.user import User
from app.repositories.audience import AudienceRepository
from app.repositories.notification import NotificationRepository
from app.schemas.notification import NotificationListResponse, NotificationRead, UnreadNotificationCount


class NotificationService:
    def __init__(
        self,
        session: AsyncSession,
        repository: NotificationRepository | None = None,
        audience: AudienceRepository | None = None,
    ) -> None:
        self.session = session
        self.repository = repository or NotificationRepository(session)
        self.audience = audience or AudienceRepository(session)

    async def notify_membership_request(
        self,
        membership: ClassMembership,
        classroom: Classroom,
    ) -> list[Notification]:
        recipients = await self.audience.list_representatives(
            classroom.id,
            exclude_user_id=membership.user_id,
        )
        actor_name = self._user_name(membership.user)
        return await self._create_for_recipients(
            recipients,
            actor_user_id=membership.user_id,
            classroom_id=classroom.id,
            event_type=NOTIFICATION_MEMBERSHIP_REQUEST,
            title="New membership request",
            message=f"{actor_name} requested to join {classroom.name}.",
            source_type="membership",
            source_id=membership.id,
            action_url=f"/classes/{classroom.id}/members",
        )

    async def notify_membership_result(
        self,
        membership: ClassMembership,
        classroom: Classroom,
        actor_user_id: int,
        *,
        approved: bool,
    ) -> list[Notification]:
        event_type = NOTIFICATION_MEMBERSHIP_APPROVED if approved else NOTIFICATION_MEMBERSHIP_REJECTED
        result = "approved" if approved else "rejected"
        return await self._create_for_recipients(
            [membership.user_id],
            actor_user_id=actor_user_id,
            classroom_id=classroom.id,
            event_type=event_type,
            title=f"Membership request {result}",
            message=f"Your request to join {classroom.name} was {result}.",
            source_type="membership",
            source_id=membership.id,
            action_url=f"/classes/{classroom.id}",
        )

    async def notify_task_created(self, task: Task, actor_user_id: int) -> list[Notification]:
        recipients = await self.audience.list_task_recipients(task, exclude_user_id=actor_user_id)
        return await self._create_for_recipients(
            recipients,
            actor_user_id=actor_user_id,
            classroom_id=task.classroom_id,
            event_type=NOTIFICATION_TASK_CREATED,
            title="New task",
            message=f"A new task was posted: {task.title}.",
            source_type="task",
            source_id=task.id,
            action_url=f"/tasks/{task.id}",
        )

    async def notify_task_updated(self, task: Task, actor_user_id: int) -> list[Notification]:
        recipients = await self.audience.list_task_recipients(task, exclude_user_id=actor_user_id)
        return await self._create_for_recipients(
            recipients,
            actor_user_id=actor_user_id,
            classroom_id=task.classroom_id,
            event_type=NOTIFICATION_TASK_UPDATED,
            title="Task updated",
            message=f"The task {task.title} was updated.",
            source_type="task",
            source_id=task.id,
            action_url=f"/tasks/{task.id}",
        )

    async def notify_announcement_posted(
        self,
        announcement: Announcement,
        actor_user_id: int,
    ) -> list[Notification]:
        if announcement.class_course_id is None:
            recipients = await self.audience.list_class_recipients(
                announcement.classroom_id,
                exclude_user_id=actor_user_id,
            )
        else:
            recipients = await self.audience.list_course_recipients(
                announcement.classroom_id,
                announcement.class_course_id,
                exclude_user_id=actor_user_id,
            )
        return await self._create_for_recipients(
            recipients,
            actor_user_id=actor_user_id,
            classroom_id=announcement.classroom_id,
            event_type=NOTIFICATION_ANNOUNCEMENT_POSTED,
            title="New announcement",
            message=announcement.title,
            source_type="announcement",
            source_id=announcement.id,
            action_url=f"/classes/{announcement.classroom_id}?tab=announcements",
        )

    async def notify_deadline_approaching(
        self,
        task: Task,
        recipient_user_id: int,
    ) -> list[Notification]:
        deadline_iso = task.deadline.isoformat() if task.deadline is not None else "none"
        return await self._create_for_recipients(
            [recipient_user_id],
            actor_user_id=None,
            classroom_id=task.classroom_id,
            event_type=NOTIFICATION_DEADLINE_APPROACHING,
            title="Deadline approaching",
            message=f"{task.title} is due soon.",
            source_type="task",
            source_id=task.id,
            action_url=f"/tasks/{task.id}",
            dedupe_key=f"deadline:{task.id}:{recipient_user_id}:{deadline_iso}:24h",
        )

    async def list_notifications(
        self,
        user_id: int,
        *,
        unread_only: bool = False,
        event_type: str | None = None,
        page: int = 1,
        page_size: int = 20,
    ) -> NotificationListResponse:
        rows, total = await self.repository.list_for_user(
            user_id,
            unread_only=unread_only,
            event_type=event_type,
            page=page,
            page_size=page_size,
        )
        return NotificationListResponse(
            items=[NotificationRead.model_validate(row) for row in rows],
            total=total,
            page=page,
            page_size=page_size,
        )

    async def count_unread(self, user_id: int) -> UnreadNotificationCount:
        return UnreadNotificationCount(unread_count=await self.repository.count_unread(user_id))

    async def mark_read(self, notification_id: int, user_id: int) -> NotificationRead:
        notification = await self.repository.mark_read(
            notification_id,
            user_id,
            datetime.now(timezone.utc),
        )
        if notification is None:
            raise self._not_found()
        await self.session.commit()
        return NotificationRead.model_validate(notification)

    async def mark_unread(self, notification_id: int, user_id: int) -> NotificationRead:
        notification = await self.repository.mark_unread(notification_id, user_id)
        if notification is None:
            raise self._not_found()
        await self.session.commit()
        return NotificationRead.model_validate(notification)

    async def mark_all_read(self, user_id: int) -> int:
        count = await self.repository.mark_all_read(user_id, datetime.now(timezone.utc))
        await self.session.commit()
        return count

    async def _get_for_recipient(self, notification_id: int, user_id: int) -> Notification:
        notification = await self.repository.get_for_recipient(
            notification_id,
            user_id,
            for_update=True,
        )
        if notification is None:
            raise self._not_found()
        return notification

    @staticmethod
    def _not_found() -> ClassFlowError:
        return ClassFlowError(
            "Notification not found",
            "NOTIFICATION_NOT_FOUND",
            status.HTTP_404_NOT_FOUND,
        )

    async def _create_for_recipients(
        self,
        recipient_user_ids: list[int],
        *,
        actor_user_id: int | None,
        classroom_id: int | None,
        event_type: str,
        title: str,
        message: str,
        source_type: str,
        source_id: int,
        action_url: str,
        dedupe_key: str | None = None,
    ) -> list[Notification]:
        rows = [
            {
                "recipient_user_id": recipient_user_id,
                "actor_user_id": actor_user_id,
                "classroom_id": classroom_id,
                "event_type": event_type,
                "title": title,
                "message": message,
                "source_type": source_type,
                "source_id": source_id,
                "action_url": action_url,
                "dedupe_key": dedupe_key,
            }
            for recipient_user_id in dict.fromkeys(recipient_user_ids)
            if recipient_user_id != actor_user_id
        ]
        if not rows:
            return []
        return await self.repository.create_many(rows)

    @staticmethod
    def _user_name(user: User) -> str:
        full_name = " ".join(part for part in (user.first_name, user.last_name) if part).strip()
        return full_name or user.username
