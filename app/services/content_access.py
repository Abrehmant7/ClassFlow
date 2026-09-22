from fastapi import status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import ClassFlowError
from app.models.classroom import CLASS_ROLE_REPRESENTATIVE, MEMBERSHIP_STATUS_APPROVED, ClassMembership
from app.repositories.classroom import ClassroomRepository
from app.repositories.course import ClassCourseRepository, CourseRegistrationRepository
from app.repositories.membership import ClassMembershipRepository


class ClassContentAccess:
    """Shared authorization for announcements and resources, including direct IDs."""

    def __init__(self, session: AsyncSession) -> None:
        self.classrooms = ClassroomRepository(session)
        self.memberships = ClassMembershipRepository(session)
        self.courses = ClassCourseRepository(session)
        self.registrations = CourseRegistrationRepository(session)

    async def approved_member(self, classroom_id: int, user_id: int) -> ClassMembership | None:
        if await self.classrooms.get_by_id(classroom_id) is None:
            return None
        membership = await self.memberships.get_by_user_and_class(user_id, classroom_id)
        if membership is None or membership.status != MEMBERSHIP_STATUS_APPROVED:
            return None
        return membership

    async def require_representative(self, classroom_id: int, user_id: int) -> ClassMembership:
        membership = await self.approved_member(classroom_id, user_id)
        if membership is None or membership.role != CLASS_ROLE_REPRESENTATIVE:
            raise ClassFlowError("Class representative access required", "CLASS_REPRESENTATIVE_REQUIRED", status.HTTP_403_FORBIDDEN)
        return membership

    async def validate_course(self, classroom_id: int, class_course_id: int | None) -> None:
        """Call before creating content or changing its course scope."""
        if class_course_id is None:
            return
        course = await self.courses.get_by_id(class_course_id)
        if course is None or course.classroom_id != classroom_id or not course.is_active:
            raise ClassFlowError("Active class course not found", "CLASS_COURSE_NOT_FOUND", status.HTTP_404_NOT_FOUND)

    async def can_read(self, classroom_id: int, class_course_id: int | None, user_id: int) -> ClassMembership | None:
        membership = await self.approved_member(classroom_id, user_id)
        if membership is None or class_course_id is None:
            return membership
        course = await self.courses.get_by_id(class_course_id)
        if course is None or course.classroom_id != classroom_id or not course.is_active:
            return None
        if membership.role == CLASS_ROLE_REPRESENTATIVE:
            return membership
        registration = await self.registrations.get_by_membership_and_class_course(membership.id, class_course_id)
        return membership if registration is not None and registration.is_active else None
