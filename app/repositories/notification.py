from datetime import datetime
from typing import Any

from sqlalchemy import func, select, update

from app.models.notification import Notification
from app.repositories.base import BaseRepository


class NotificationRepository(BaseRepository[Notification]):
    async def create_many(self, rows: list[dict[str, Any]]) -> list[Notification]:
        notifications = [Notification(**row) for row in rows]
        self.session.add_all(notifications)
        await self.session.flush()
        return notifications

    async def get_for_recipient(
        self,
        notification_id: int,
        recipient_user_id: int,
        *,
        for_update: bool = False,
    ) -> Notification | None:
        statement = select(Notification).where(
            Notification.id == notification_id,
            Notification.recipient_user_id == recipient_user_id,
        )
        if for_update:
            statement = statement.with_for_update().execution_options(populate_existing=True)
        return await self.session.scalar(statement)

    async def list_for_user(
        self,
        recipient_user_id: int,
        *,
        unread_only: bool = False,
        event_type: str | None = None,
        page: int = 1,
        page_size: int = 20,
    ) -> tuple[list[Notification], int]:
        conditions = [Notification.recipient_user_id == recipient_user_id]
        if unread_only:
            conditions.append(Notification.is_read.is_(False))
        if event_type is not None:
            conditions.append(Notification.event_type == event_type)

        total = await self.session.scalar(
            select(func.count(Notification.id)).where(*conditions)
        )
        notifications = list((await self.session.scalars(
            select(Notification)
            .where(*conditions)
            .order_by(Notification.created_at.desc(), Notification.id.desc())
            .offset((page - 1) * page_size)
            .limit(page_size)
        )).all())
        return notifications, int(total or 0)

    async def count_unread(self, recipient_user_id: int) -> int:
        count = await self.session.scalar(
            select(func.count(Notification.id)).where(
                Notification.recipient_user_id == recipient_user_id,
                Notification.is_read.is_(False),
            )
        )
        return int(count or 0)

    async def mark_read(
        self,
        notification_id: int,
        recipient_user_id: int,
        read_at: datetime,
    ) -> Notification | None:
        return await self.session.scalar(
            update(Notification)
            .where(
                Notification.id == notification_id,
                Notification.recipient_user_id == recipient_user_id,
            )
            .values(is_read=True, read_at=read_at)
            .returning(Notification)
        )

    async def mark_unread(
        self,
        notification_id: int,
        recipient_user_id: int,
    ) -> Notification | None:
        return await self.session.scalar(
            update(Notification)
            .where(
                Notification.id == notification_id,
                Notification.recipient_user_id == recipient_user_id,
            )
            .values(is_read=False, read_at=None)
            .returning(Notification)
        )

    async def mark_all_read(self, recipient_user_id: int, read_at: datetime) -> int:
        result = await self.session.execute(
            update(Notification)
            .where(
                Notification.recipient_user_id == recipient_user_id,
                Notification.is_read.is_(False),
            )
            .values(is_read=True, read_at=read_at)
        )
        await self.session.flush()
        return int(result.rowcount or 0)
