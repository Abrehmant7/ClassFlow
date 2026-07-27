from sqlalchemy import select

from app.models.classroom import Classroom, ClassMembership, MEMBERSHIP_STATUS_REMOVED
from app.repositories.base import BaseRepository
from app.schemas.classroom import ClassroomCreate, ClassroomUpdate


class ClassroomRepository(BaseRepository[Classroom]):
    async def get_by_id(self, classroom_id: int, include_inactive: bool = False) -> Classroom | None:
        statement = select(Classroom).where(Classroom.id == classroom_id)

        if not include_inactive:
            statement = statement.where(Classroom.is_active.is_(True))

        result = await self.session.execute(statement)
        return result.scalar_one_or_none()

    async def get_by_join_code(self, join_code: str) -> Classroom | None:
        result = await self.session.execute(
            select(Classroom).where(Classroom.join_code == join_code)
        )
        return result.scalar_one_or_none()

    async def list_for_user(self, user_id: int) -> list[tuple[Classroom, ClassMembership]]:
        result = await self.session.execute(
            select(Classroom, ClassMembership)
            .join(ClassMembership, ClassMembership.classroom_id == Classroom.id)
            .where(
                ClassMembership.user_id == user_id,
                ClassMembership.status != MEMBERSHIP_STATUS_REMOVED,
                Classroom.is_active.is_(True),
            )
            .order_by(Classroom.created_at.desc())
        )
        return [(classroom, membership) for classroom, membership in result.all()]

    async def create(self, classroom_in: ClassroomCreate, creator_id: int, join_code: str) -> Classroom:
        classroom = Classroom(
            name=classroom_in.name,
            semester=classroom_in.semester,
            section=classroom_in.section,
            description=classroom_in.description,
            join_code=join_code,
            creator_id=creator_id,
        )
        self.session.add(classroom)
        await self.session.flush()
        return classroom

    async def update(self, classroom: Classroom, classroom_in: ClassroomUpdate) -> Classroom:
        update_data = classroom_in.model_dump(exclude_unset=True)

        for field, value in update_data.items():
            setattr(classroom, field, value)

        await self.session.flush()
        return classroom