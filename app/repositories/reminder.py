from datetime import datetime

from sqlalchemy import select, update

from app.models.reminder import (
    REMINDER_CANCELLED,
    REMINDER_PENDING,
    REMINDER_SENT,
    Reminder,
)
from app.models.task import Task
from app.repositories.base import BaseRepository


class ReminderRepository(BaseRepository[Reminder]):
    async def get_unique(
        self,
        task_id: int,
        recipient_user_id: int,
        remind_at: datetime,
    ) -> Reminder | None:
        return await self.session.scalar(
            select(Reminder).where(
                Reminder.task_id == task_id,
                Reminder.recipient_user_id == recipient_user_id,
                Reminder.remind_at == remind_at,
            )
        )

    async def ensure_pending(
        self,
        task_id: int,
        recipient_user_id: int,
        remind_at: datetime,
        deadline_snapshot: datetime,
    ) -> Reminder:
        reminder = await self.get_unique(task_id, recipient_user_id, remind_at)
        if reminder is None:
            reminder = Reminder(
                task_id=task_id,
                recipient_user_id=recipient_user_id,
                remind_at=remind_at,
                deadline_snapshot=deadline_snapshot,
                status=REMINDER_PENDING,
            )
            self.session.add(reminder)
        elif reminder.status == REMINDER_CANCELLED:
            reminder.status = REMINDER_PENDING
            reminder.deadline_snapshot = deadline_snapshot
            reminder.sent_at = None
        await self.session.flush()
        return reminder

    async def cancel_pending_for_task(self, task_id: int) -> int:
        return await self._cancel_where(Reminder.task_id == task_id)

    async def cancel_pending_for_user_task(self, task_id: int, recipient_user_id: int) -> int:
        return await self._cancel_where(
            Reminder.task_id == task_id,
            Reminder.recipient_user_id == recipient_user_id,
        )

    async def cancel_pending_for_user_class(self, classroom_id: int, recipient_user_id: int) -> int:
        task_ids = select(Task.id).where(Task.classroom_id == classroom_id)
        return await self._cancel_where(
            Reminder.task_id.in_(task_ids),
            Reminder.recipient_user_id == recipient_user_id,
        )

    async def cancel_pending_for_user_course(self, class_course_id: int, recipient_user_id: int) -> int:
        task_ids = select(Task.id).where(Task.class_course_id == class_course_id)
        return await self._cancel_where(
            Reminder.task_id.in_(task_ids),
            Reminder.recipient_user_id == recipient_user_id,
        )

    async def lock_due(self, now: datetime, limit: int) -> list[Reminder]:
        return list((await self.session.scalars(
            select(Reminder)
            .where(
                Reminder.status == REMINDER_PENDING,
                Reminder.remind_at <= now,
            )
            .order_by(Reminder.remind_at.asc(), Reminder.id.asc())
            .limit(limit)
            .with_for_update(skip_locked=True)
        )).all())

    async def mark_sent(self, reminder: Reminder, sent_at: datetime) -> None:
        reminder.status = REMINDER_SENT
        reminder.sent_at = sent_at
        await self.session.flush()

    async def mark_cancelled(self, reminder: Reminder) -> None:
        reminder.status = REMINDER_CANCELLED
        await self.session.flush()

    async def _cancel_where(self, *conditions) -> int:
        result = await self.session.execute(
            update(Reminder)
            .where(Reminder.status == REMINDER_PENDING, *conditions)
            .values(status=REMINDER_CANCELLED)
        )
        await self.session.flush()
        return int(result.rowcount or 0)
