from datetime import datetime, timedelta, timezone

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.models.task import TASK_STATUS_ACTIVE, TASK_VISIBILITY_PERSONAL, Task
from app.repositories.audience import AudienceRepository, task_access_condition
from app.repositories.reminder import ReminderRepository
from app.repositories.task import TaskRepository
from app.services.notification import NotificationService


class ReminderService:
    def __init__(
        self,
        session: AsyncSession,
        repository: ReminderRepository | None = None,
        audience: AudienceRepository | None = None,
        task_repository: TaskRepository | None = None,
        notification_service: NotificationService | None = None,
    ) -> None:
        self.session = session
        self.repository = repository or ReminderRepository(session)
        self.audience = audience or AudienceRepository(session)
        self.task_repository = task_repository or TaskRepository(session)
        self.notification_service = notification_service or NotificationService(
            session,
            audience=self.audience,
        )

    async def sync_task_reminders(self, task: Task, now: datetime | None = None) -> int:
        now = now or datetime.now(timezone.utc)
        await self.repository.cancel_pending_for_task(task.id)
        if not self._can_schedule(task, now):
            return 0

        if task.visibility == TASK_VISIBILITY_PERSONAL:
            recipients = [task.created_by_user_id]
        else:
            recipients = await self.audience.list_task_recipients(
                task,
                students_only=True,
                incomplete_only=True,
            )
        remind_at = self._remind_at(task.deadline, now)
        for recipient_user_id in recipients:
            await self.repository.ensure_pending(
                task.id,
                recipient_user_id,
                remind_at,
                task.deadline,
            )
        return len(recipients)

    async def cancel_task_reminders(self, task_id: int) -> int:
        return await self.repository.cancel_pending_for_task(task_id)

    async def cancel_user_task_reminder(self, task_id: int, user_id: int) -> int:
        return await self.repository.cancel_pending_for_user_task(task_id, user_id)

    async def restore_user_task_reminder(
        self,
        task_id: int,
        user_id: int,
        now: datetime | None = None,
    ) -> bool:
        now = now or datetime.now(timezone.utc)
        task = await self.task_repository.get_by_id(task_id)
        if task is None or not self._can_schedule(task, now):
            return False
        if task.visibility == TASK_VISIBILITY_PERSONAL:
            authorized = task.created_by_user_id == user_id
        else:
            authorized = user_id in await self.audience.list_task_recipients(
                task,
                students_only=True,
                incomplete_only=True,
            )
        if not authorized:
            return False
        await self.repository.ensure_pending(
            task.id,
            user_id,
            self._remind_at(task.deadline, now),
            task.deadline,
        )
        return True

    async def sync_user_class_reminders(
        self,
        classroom_id: int,
        user_id: int,
        now: datetime | None = None,
    ) -> int:
        now = now or datetime.now(timezone.utc)
        tasks = list((await self.session.scalars(
            select(Task).where(
                Task.classroom_id == classroom_id,
                Task.status == TASK_STATUS_ACTIVE,
                Task.deadline > now,
                task_access_condition(user_id),
            )
        )).all())
        restored = 0
        for task in tasks:
            restored += int(await self.restore_user_task_reminder(task.id, user_id, now))
        return restored

    async def cancel_user_class_reminders(self, classroom_id: int, user_id: int) -> int:
        return await self.repository.cancel_pending_for_user_class(classroom_id, user_id)

    async def sync_user_course_reminders(
        self,
        class_course_id: int,
        user_id: int,
        now: datetime | None = None,
    ) -> int:
        now = now or datetime.now(timezone.utc)
        task_ids = list((await self.session.scalars(
            select(Task.id).where(
                Task.class_course_id == class_course_id,
                Task.status == TASK_STATUS_ACTIVE,
                Task.deadline > now,
                task_access_condition(user_id),
            )
        )).all())
        restored = 0
        for task_id in task_ids:
            restored += int(await self.restore_user_task_reminder(task_id, user_id, now))
        return restored

    async def cancel_user_course_reminders(self, class_course_id: int, user_id: int) -> int:
        return await self.repository.cancel_pending_for_user_course(class_course_id, user_id)

    async def process_due_reminders(self, now: datetime | None = None) -> int:
        now = now or datetime.now(timezone.utc)
        reminders = await self.repository.lock_due(now, settings.REMINDER_BATCH_SIZE)
        sent = 0
        try:
            for reminder in reminders:
                task = await self.task_repository.get_by_id(reminder.task_id)
                if not await self._reminder_is_current(reminder, task, now):
                    await self.repository.mark_cancelled(reminder)
                    continue
                await self.notification_service.notify_deadline_approaching(
                    task,
                    reminder.recipient_user_id,
                )
                await self.repository.mark_sent(reminder, now)
                sent += 1
            await self.session.commit()
        except Exception:
            await self.session.rollback()
            raise
        return sent

    async def _reminder_is_current(self, reminder, task: Task | None, now: datetime) -> bool:
        if task is None or not self._can_schedule(task, now):
            return False
        if task.deadline != reminder.deadline_snapshot:
            return False
        if task.visibility == TASK_VISIBILITY_PERSONAL:
            return task.created_by_user_id == reminder.recipient_user_id
        recipients = await self.audience.list_task_recipients(
            task,
            students_only=True,
            incomplete_only=True,
        )
        return reminder.recipient_user_id in recipients

    @staticmethod
    def _can_schedule(task: Task, now: datetime) -> bool:
        return (
            task.status == TASK_STATUS_ACTIVE
            and task.deadline is not None
            and task.deadline > now
        )

    @staticmethod
    def _remind_at(deadline: datetime, now: datetime) -> datetime:
        scheduled = deadline - timedelta(minutes=settings.REMINDER_LEAD_MINUTES)
        return max(scheduled, now)
