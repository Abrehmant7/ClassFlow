from datetime import datetime

from sqlalchemy import or_, select
from sqlalchemy.orm import selectinload

from app.models.course import ClassCourse, Course, CourseRegistration
from app.repositories.base import BaseRepository
from app.schemas.course import ClassCourseCreate, ClassCourseUpdate


class CourseRepository(BaseRepository[Course]):
    async def list(self, search: str | None = None) -> list[Course]:
        statement = select(Course).order_by(Course.name.asc())

        if search:
            term = f"%{search.strip()}%"
            statement = statement.where(
                or_(
                    Course.name.ilike(term),
                    Course.code.ilike(term),
                )
            )

        result = await self.session.execute(statement)
        return list(result.scalars().all())

    async def get_by_id(self, course_id: int) -> Course | None:
        result = await self.session.execute(select(Course).where(Course.id == course_id))
        return result.scalar_one_or_none()

    async def get_by_code(self, code: str) -> Course | None:
        result = await self.session.execute(select(Course).where(Course.code == code))
        return result.scalar_one_or_none()

    async def get_by_normalized_name(self, name: str) -> Course | None:
        result = await self.session.execute(select(Course).where(Course.name.ilike(name)))
        return result.scalar_one_or_none()

    async def create(self, name: str, code: str, description: str | None) -> Course:
        course = Course(name=name, code=code, description=description)
        self.session.add(course)
        await self.session.flush()
        return course


class ClassCourseRepository(BaseRepository[ClassCourse]):
    async def get_by_id(self, class_course_id: int) -> ClassCourse | None:
        result = await self.session.execute(
            select(ClassCourse)
            .options(selectinload(ClassCourse.course))
            .where(ClassCourse.id == class_course_id)
        )
        return result.scalar_one_or_none()

    async def get_by_class_and_course(self, classroom_id: int, course_id: int) -> ClassCourse | None:
        result = await self.session.execute(
            select(ClassCourse)
            .options(selectinload(ClassCourse.course))
            .where(
                ClassCourse.classroom_id == classroom_id,
                ClassCourse.course_id == course_id,
            )
        )
        return result.scalar_one_or_none()

    async def list_for_class(self, classroom_id: int, include_inactive: bool = False) -> list[ClassCourse]:
        statement = (
            select(ClassCourse)
            .options(selectinload(ClassCourse.course))
            .where(ClassCourse.classroom_id == classroom_id)
            .order_by(ClassCourse.created_at.desc())
        )

        if not include_inactive:
            statement = statement.where(ClassCourse.is_active.is_(True))

        result = await self.session.execute(statement)
        return list(result.scalars().all())

    async def list_active_default_for_class(self, classroom_id: int) -> list[ClassCourse]:
        result = await self.session.execute(
            select(ClassCourse)
            .options(selectinload(ClassCourse.course))
            .where(
                ClassCourse.classroom_id == classroom_id,
                ClassCourse.is_active.is_(True),
                ClassCourse.is_default.is_(True),
            )
        )
        return list(result.scalars().all())

    async def create(self, classroom_id: int, class_course_in: ClassCourseCreate, created_by_user_id: int) -> ClassCourse:
        class_course = ClassCourse(
            classroom_id=classroom_id,
            course_id=class_course_in.course_id,
            instructor_name=class_course_in.instructor_name,
            is_default=class_course_in.is_default,
            created_by_user_id=created_by_user_id,
        )
        self.session.add(class_course)
        await self.session.flush()
        return class_course

    async def update(self, class_course: ClassCourse, class_course_in: ClassCourseUpdate) -> ClassCourse:
        update_data = class_course_in.model_dump(exclude_unset=True)

        for field, value in update_data.items():
            setattr(class_course, field, value)

        await self.session.flush()
        return class_course

    async def deactivate(self, class_course: ClassCourse) -> ClassCourse:
        class_course.is_active = False
        await self.session.flush()
        return class_course


class CourseRegistrationRepository(BaseRepository[CourseRegistration]):
    async def get_by_membership_and_class_course(self, membership_id: int, class_course_id: int) -> CourseRegistration | None:
        result = await self.session.execute(
            select(CourseRegistration)
            .options(
                selectinload(CourseRegistration.class_course).selectinload(ClassCourse.course)
            )
            .where(
                CourseRegistration.membership_id == membership_id,
                CourseRegistration.class_course_id == class_course_id,
            )
        )
        return result.scalar_one_or_none()

    async def list_active_for_membership(self, membership_id: int) -> list[CourseRegistration]:
        result = await self.session.execute(
            select(CourseRegistration)
            .options(
                selectinload(CourseRegistration.class_course).selectinload(ClassCourse.course)
            )
            .join(ClassCourse, ClassCourse.id == CourseRegistration.class_course_id)
            .where(
                CourseRegistration.membership_id == membership_id,
                CourseRegistration.is_active.is_(True),
                ClassCourse.is_active.is_(True),
            )
            .order_by(ClassCourse.created_at.desc())
        )
        return list(result.scalars().all())

    async def create(self, membership_id: int, class_course_id: int) -> CourseRegistration:
        registration = CourseRegistration(
            membership_id=membership_id,
            class_course_id=class_course_id,
        )
        self.session.add(registration)
        await self.session.flush()
        return registration

    async def reactivate(self, registration: CourseRegistration, registered_at: datetime) -> CourseRegistration:
        registration.is_active = True
        registration.registered_at = registered_at
        registration.dropped_at = None
        await self.session.flush()
        return registration

    async def drop(self, registration: CourseRegistration, dropped_at: datetime) -> CourseRegistration:
        registration.is_active = False
        registration.dropped_at = dropped_at
        await self.session.flush()
        return registration