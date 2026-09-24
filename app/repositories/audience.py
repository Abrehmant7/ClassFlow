from sqlalchemy import and_, exists, or_, select
from sqlalchemy.orm import aliased

from app.models.classroom import (
    CLASS_ROLE_REPRESENTATIVE,
    CLASS_ROLE_STUDENT,
    MEMBERSHIP_STATUS_APPROVED,
    ClassMembership,
    Classroom,
)
from app.models.course import ClassCourse, CourseRegistration
from app.models.task import (
    TASK_PROGRESS_COMPLETED,
    TASK_VISIBILITY_PERSONAL,
    TASK_VISIBILITY_SHARED,
    Task,
    TaskProgress,
)
from app.models.user import User
from app.repositories.base import BaseRepository


def approved_class_access_condition(user_id: int, classroom_id):
    """Return a correlated condition for an active, approved class membership."""
    membership = aliased(ClassMembership)
    classroom = aliased(Classroom)
    return exists(
        select(membership.id)
        .join(classroom, classroom.id == membership.classroom_id)
        .where(
            membership.user_id == user_id,
            membership.classroom_id == classroom_id,
            membership.status == MEMBERSHIP_STATUS_APPROVED,
            classroom.is_active.is_(True),
        )
    )


def active_course_access_condition(user_id: int, classroom_id, class_course_id):
    """Grant active course access to representatives or registered students."""
    membership = aliased(ClassMembership)
    classroom = aliased(Classroom)
    class_course = aliased(ClassCourse)
    registration = aliased(CourseRegistration)
    active_registration = exists(
        select(registration.id).where(
            registration.membership_id == membership.id,
            registration.class_course_id == class_course.id,
            registration.is_active.is_(True),
        )
    )
    return exists(
        select(membership.id)
        .join(classroom, classroom.id == membership.classroom_id)
        .join(
            class_course,
            and_(
                class_course.id == class_course_id,
                class_course.classroom_id == classroom_id,
            ),
        )
        .where(
            membership.user_id == user_id,
            membership.classroom_id == classroom_id,
            membership.status == MEMBERSHIP_STATUS_APPROVED,
            classroom.is_active.is_(True),
            class_course.is_active.is_(True),
            or_(
                membership.role == CLASS_ROLE_REPRESENTATIVE,
                active_registration,
            ),
        )
    )


def task_access_condition(user_id: int):
    """Shared task visibility for feed, search, dashboard, and notifications."""
    active_personal_scope = or_(
        Task.class_course_id.is_(None),
        exists(
            select(ClassCourse.id)
            .where(
                ClassCourse.id == Task.class_course_id,
                ClassCourse.classroom_id == Task.classroom_id,
                ClassCourse.is_active.is_(True),
            )
            .correlate(Task)
        ),
    )
    return or_(
        and_(
            Task.visibility == TASK_VISIBILITY_PERSONAL,
            Task.created_by_user_id == user_id,
            active_personal_scope,
        ),
        and_(
            Task.visibility == TASK_VISIBILITY_SHARED,
            Task.class_course_id.is_(None),
            approved_class_access_condition(user_id, Task.classroom_id),
        ),
        and_(
            Task.visibility == TASK_VISIBILITY_SHARED,
            Task.class_course_id.is_not(None),
            active_course_access_condition(user_id, Task.classroom_id, Task.class_course_id),
        ),
    )


class AudienceRepository(BaseRepository[ClassMembership]):
    async def list_class_recipients(
        self,
        classroom_id: int,
        *,
        exclude_user_id: int | None = None,
        students_only: bool = False,
        task_id_for_incomplete: int | None = None,
    ) -> list[int]:
        return await self._list_recipients(
            classroom_id,
            exclude_user_id=exclude_user_id,
            students_only=students_only,
            task_id_for_incomplete=task_id_for_incomplete,
        )

    async def list_course_recipients(
        self,
        classroom_id: int,
        class_course_id: int,
        *,
        exclude_user_id: int | None = None,
        students_only: bool = False,
        task_id_for_incomplete: int | None = None,
    ) -> list[int]:
        return await self._list_recipients(
            classroom_id,
            class_course_id=class_course_id,
            exclude_user_id=exclude_user_id,
            students_only=students_only,
            task_id_for_incomplete=task_id_for_incomplete,
        )

    async def list_representatives(
        self,
        classroom_id: int,
        *,
        exclude_user_id: int | None = None,
    ) -> list[int]:
        return await self._list_recipients(
            classroom_id,
            representatives_only=True,
            exclude_user_id=exclude_user_id,
        )

    async def list_task_recipients(
        self,
        task: Task,
        *,
        exclude_user_id: int | None = None,
        students_only: bool = False,
        incomplete_only: bool = False,
    ) -> list[int]:
        if task.visibility == TASK_VISIBILITY_PERSONAL:
            if exclude_user_id == task.created_by_user_id:
                return []
            result = await self.session.scalar(
                select(User.id).where(User.id == task.created_by_user_id, User.is_active.is_(True))
            )
            return [] if result is None else [result]
        if task.visibility != TASK_VISIBILITY_SHARED or task.classroom_id is None:
            return []

        options = {
            "exclude_user_id": exclude_user_id,
            "students_only": students_only,
            "task_id_for_incomplete": task.id if incomplete_only else None,
        }
        if task.class_course_id is None:
            return await self.list_class_recipients(task.classroom_id, **options)
        return await self.list_course_recipients(
            task.classroom_id,
            task.class_course_id,
            **options,
        )

    async def _list_recipients(
        self,
        classroom_id: int,
        *,
        class_course_id: int | None = None,
        representatives_only: bool = False,
        students_only: bool = False,
        exclude_user_id: int | None = None,
        task_id_for_incomplete: int | None = None,
    ) -> list[int]:
        statement = (
            select(ClassMembership.user_id)
            .join(Classroom, Classroom.id == ClassMembership.classroom_id)
            .join(User, User.id == ClassMembership.user_id)
            .where(
                ClassMembership.classroom_id == classroom_id,
                ClassMembership.status == MEMBERSHIP_STATUS_APPROVED,
                Classroom.is_active.is_(True),
                User.is_active.is_(True),
            )
        )
        if class_course_id is not None:
            registration = aliased(CourseRegistration)
            statement = (
                statement
                .join(
                    ClassCourse,
                    and_(
                        ClassCourse.id == class_course_id,
                        ClassCourse.classroom_id == ClassMembership.classroom_id,
                    ),
                )
                .outerjoin(
                    registration,
                    and_(
                        registration.membership_id == ClassMembership.id,
                        registration.class_course_id == ClassCourse.id,
                        registration.is_active.is_(True),
                    ),
                )
                .where(
                    ClassCourse.is_active.is_(True),
                    or_(
                        ClassMembership.role == CLASS_ROLE_REPRESENTATIVE,
                        registration.id.is_not(None),
                    ),
                )
            )
        if representatives_only:
            statement = statement.where(ClassMembership.role == CLASS_ROLE_REPRESENTATIVE)
        if students_only:
            statement = statement.where(ClassMembership.role == CLASS_ROLE_STUDENT)
        if exclude_user_id is not None:
            statement = statement.where(ClassMembership.user_id != exclude_user_id)
        if task_id_for_incomplete is not None:
            statement = statement.where(
                ~exists(
                    select(TaskProgress.id).where(
                        TaskProgress.task_id == task_id_for_incomplete,
                        TaskProgress.membership_id == ClassMembership.id,
                        TaskProgress.status == TASK_PROGRESS_COMPLETED,
                    )
                )
            )
        result = await self.session.scalars(
            statement.distinct().order_by(ClassMembership.user_id.asc())
        )
        return list(result.all())
