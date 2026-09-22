from fastapi import status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import ClassFlowError
from app.models.announcement import Announcement
from app.models.classroom import CLASS_ROLE_REPRESENTATIVE, ClassMembership
from app.repositories.announcement import AnnouncementRepository
from app.schemas.announcement import AnnouncementCreate, AnnouncementRead, AnnouncementUpdate
from app.services.content_access import ClassContentAccess
from app.services.rag import RagChatService


class AnnouncementService:
    def __init__(
        self,
        session: AsyncSession,
        repository: AnnouncementRepository | None = None,
        access: ClassContentAccess | None = None,
        rag_service: RagChatService | None = None,
    ) -> None:
        self.session = session
        self.repository = repository or AnnouncementRepository(session)
        self.access = access or ClassContentAccess(session)
        self.rag_service = rag_service or RagChatService(session)

    async def create_announcement(self, classroom_id: int, announcement_in: AnnouncementCreate, user_id: int) -> AnnouncementRead:
        membership = await self.access.require_representative(classroom_id, user_id)
        await self.access.validate_course(classroom_id, announcement_in.class_course_id)
        try:
            announcement = await self.repository.create(classroom_id, user_id, announcement_in)
            await self.rag_service.index_announcement(announcement)
            await self.session.commit()
        except Exception:
            await self.session.rollback()
            raise
        await self.session.refresh(announcement)
        return self._read(announcement, membership)

    async def list_announcements(self, classroom_id: int, user_id: int) -> list[AnnouncementRead]:
        membership = await self.access.approved_member(classroom_id, user_id)
        if membership is None:
            raise self._not_found()
        announcements = await self.repository.list_accessible_for_class(classroom_id, user_id)
        return [self._read(announcement, membership) for announcement in announcements]

    async def get_announcement(self, announcement_id: int, user_id: int) -> AnnouncementRead:
        announcement, membership = await self._authorized_announcement(announcement_id, user_id)
        return self._read(announcement, membership)

    async def update_announcement(self, announcement_id: int, announcement_in: AnnouncementUpdate, user_id: int) -> AnnouncementRead:
        announcement, membership = await self._authorized_announcement(announcement_id, user_id, manage=True)
        if not announcement_in.model_fields_set:
            return self._read(announcement, membership)
        if "class_course_id" in announcement_in.model_fields_set:
            await self.access.validate_course(announcement.classroom_id, announcement_in.class_course_id)
        try:
            announcement = await self.repository.update(announcement, announcement_in)
            await self.rag_service.index_announcement(announcement)
            await self.session.commit()
        except Exception:
            await self.session.rollback()
            raise
        await self.session.refresh(announcement)
        return self._read(announcement, membership)

    async def delete_announcement(self, announcement_id: int, user_id: int) -> None:
        announcement, _membership = await self._authorized_announcement(announcement_id, user_id, manage=True)
        try:
            await self.rag_service.delete_announcement(announcement_id)
            await self.repository.delete(announcement)
            await self.session.commit()
        except Exception:
            await self.session.rollback()
            raise

    async def _authorized_announcement(
        self, announcement_id: int, user_id: int, *, manage: bool = False,
    ) -> tuple[Announcement, ClassMembership]:
        announcement = await self.repository.get_by_id(announcement_id, for_update=manage)
        if announcement is None:
            raise self._not_found()
        membership = await self.access.can_read(announcement.classroom_id, announcement.class_course_id, user_id)
        if membership is None:
            raise self._not_found()
        if manage and membership.role != CLASS_ROLE_REPRESENTATIVE:
            raise ClassFlowError("Class representative access required", "CLASS_REPRESENTATIVE_REQUIRED", status.HTTP_403_FORBIDDEN)
        return announcement, membership

    @staticmethod
    def _read(announcement: Announcement, membership: ClassMembership) -> AnnouncementRead:
        return AnnouncementRead.model_validate({
            **{field: getattr(announcement, field) for field in AnnouncementRead.model_fields if field != "can_manage"},
            "can_manage": membership.role == CLASS_ROLE_REPRESENTATIVE,
        })

    @staticmethod
    def _not_found() -> ClassFlowError:
        return ClassFlowError("Announcement not found", "ANNOUNCEMENT_NOT_FOUND", status.HTTP_404_NOT_FOUND)
