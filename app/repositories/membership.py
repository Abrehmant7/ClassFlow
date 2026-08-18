from datetime import datetime

from sqlalchemy import select
from sqlalchemy.orm import selectinload

from app.models.classroom import ClassMembership
from app.repositories.base import BaseRepository


class ClassMembershipRepository(BaseRepository[ClassMembership]):
    async def get_by_id(self, membership_id: int) -> ClassMembership | None:
        result = await self.session.execute(
            select(ClassMembership)
            .options(selectinload(ClassMembership.user))
            .where(ClassMembership.id == membership_id)
        )
        return result.scalar_one_or_none()

    async def get_by_user_and_class(self, user_id: int, classroom_id: int) -> ClassMembership | None:
        result = await self.session.execute(
            select(ClassMembership)
            .options(selectinload(ClassMembership.user))
            .where(
                ClassMembership.user_id == user_id,
                ClassMembership.classroom_id == classroom_id,
            )
        )
        return result.scalar_one_or_none()

    async def list_pending_for_class(self, classroom_id: int) -> list[ClassMembership]:
        result = await self.session.execute(
            select(ClassMembership)
            .options(selectinload(ClassMembership.user))
            .where(
                ClassMembership.classroom_id == classroom_id,
                ClassMembership.status == "pending",
            )
            .order_by(ClassMembership.requested_at.asc())
        )
        return list(result.scalars().all())

    async def list_approved_for_class(self, classroom_id: int) -> list[ClassMembership]:
        result = await self.session.execute(
            select(ClassMembership)
            .options(selectinload(ClassMembership.user))
            .where(
                ClassMembership.classroom_id == classroom_id,
                ClassMembership.status == "approved",
            )
            .order_by(ClassMembership.role.asc(), ClassMembership.requested_at.asc())
        )
        return list(result.scalars().all())

    async def create(
        self,
        user_id: int,
        classroom_id: int,
        role: str,
        status: str,
        responded_at: datetime | None = None,
    ) -> ClassMembership:
        membership = ClassMembership(
            user_id=user_id,
            classroom_id=classroom_id,
            role=role,
            status=status,
            responded_at=responded_at,
        )
        self.session.add(membership)
        await self.session.flush()
        return membership

    async def update_status(
        self,
        membership: ClassMembership,
        status: str,
        responded_at: datetime | None,
    ) -> ClassMembership:
        membership.status = status
        membership.responded_at = responded_at
        await self.session.flush()
        return membership

    async def reset_as_pending_request(
        self,
        membership: ClassMembership,
        requested_at: datetime,
    ) -> ClassMembership:
        membership.role = "student"
        membership.status = "pending"
        membership.requested_at = requested_at
        membership.responded_at = None
        await self.session.flush()
        return membership

    async def has_approved_representative_membership(self, user_id: int) -> bool:
        result = await self.session.execute(
            select(ClassMembership.id)
            .where(
                ClassMembership.user_id == user_id,
                ClassMembership.status == "approved",
                ClassMembership.role == "representative",
            )
            .limit(1)
        )
        return result.scalar_one_or_none() is not None
