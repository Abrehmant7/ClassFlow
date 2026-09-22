from sqlalchemy import select

from app.models.announcement import Announcement
from app.repositories.base import BaseRepository
from app.repositories.content_access import accessible_class_content
from app.schemas.announcement import AnnouncementCreate, AnnouncementUpdate


class AnnouncementRepository(BaseRepository[Announcement]):
    async def create(self, classroom_id: int, created_by_user_id: int, announcement_in: AnnouncementCreate) -> Announcement:
        announcement = Announcement(
            classroom_id=classroom_id,
            created_by_user_id=created_by_user_id,
            **announcement_in.model_dump(),
        )
        self.session.add(announcement)
        await self.session.flush()
        return announcement

    async def get_by_id(self, announcement_id: int, *, for_update: bool = False) -> Announcement | None:
        statement = select(Announcement).where(Announcement.id == announcement_id)
        if for_update:
            statement = statement.with_for_update().execution_options(populate_existing=True)
        return await self.session.scalar(statement)

    async def list_accessible_for_class(self, classroom_id: int, user_id: int) -> list[Announcement]:
        result = await self.session.scalars(
            select(Announcement)
            .where(Announcement.classroom_id == classroom_id, accessible_class_content(Announcement, user_id))
            .order_by(Announcement.is_pinned.desc(), Announcement.created_at.desc(), Announcement.id.desc())
        )
        return list(result.all())

    async def update(self, announcement: Announcement, announcement_in: AnnouncementUpdate) -> Announcement:
        for field, value in announcement_in.model_dump(exclude_unset=True).items():
            setattr(announcement, field, value)
        await self.session.flush()
        return announcement

    async def delete(self, announcement: Announcement) -> None:
        await self.session.delete(announcement)
        await self.session.flush()
