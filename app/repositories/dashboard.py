from typing import NamedTuple

from sqlalchemy import exists, func, select
from sqlalchemy.orm import aliased, selectinload

from app.models.announcement import Announcement
from app.models.classroom import (
    CLASS_ROLE_REPRESENTATIVE,
    MEMBERSHIP_STATUS_APPROVED,
    MEMBERSHIP_STATUS_PENDING,
    ClassMembership,
    Classroom,
)
from app.repositories.base import BaseRepository
from app.repositories.content_access import accessible_class_content


class PendingMembershipResult(NamedTuple):
    items: list[ClassMembership]
    total: int


class DashboardRepository(BaseRepository[Announcement]):
    async def list_recent_announcements(self, user_id: int, limit: int) -> list[Announcement]:
        result = await self.session.scalars(
            select(Announcement)
            .where(accessible_class_content(Announcement, user_id))
            .order_by(Announcement.created_at.desc(), Announcement.id.desc())
            .limit(limit)
        )
        return list(result.all())

    async def list_pending_membership_requests(
        self,
        user_id: int,
        limit: int,
    ) -> PendingMembershipResult:
        representative = aliased(ClassMembership)
        representative_access = exists(
            select(representative.id).where(
                representative.user_id == user_id,
                representative.classroom_id == ClassMembership.classroom_id,
                representative.role == CLASS_ROLE_REPRESENTATIVE,
                representative.status == MEMBERSHIP_STATUS_APPROVED,
            )
        ).correlate(ClassMembership)
        conditions = (
            ClassMembership.status == MEMBERSHIP_STATUS_PENDING,
            Classroom.is_active.is_(True),
            representative_access,
        )
        total = int(await self.session.scalar(
            select(func.count(ClassMembership.id))
            .join(Classroom, Classroom.id == ClassMembership.classroom_id)
            .where(*conditions)
        ) or 0)
        items = list((await self.session.scalars(
            select(ClassMembership)
            .join(Classroom, Classroom.id == ClassMembership.classroom_id)
            .options(
                selectinload(ClassMembership.user),
                selectinload(ClassMembership.classroom),
            )
            .where(*conditions)
            .order_by(ClassMembership.requested_at.asc(), ClassMembership.id.asc())
            .limit(limit)
        )).all())
        return PendingMembershipResult(items=items, total=total)
