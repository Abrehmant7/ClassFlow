from datetime import datetime, timezone

import pytest

from app.core.exceptions import ClassFlowError
from app.models.classroom import MEMBERSHIP_STATUS_APPROVED, ClassMembership
from app.models.course import ClassCourse, CourseRegistration
from app.services.course import CourseRegistrationService


class FakeSession:
    def __init__(self) -> None:
        self.committed = False

    async def commit(self) -> None:
        self.committed = True


class FakeMembershipRepository:
    def __init__(self, memberships: list[ClassMembership]) -> None:
        self.memberships = {
            (membership.user_id, membership.classroom_id): membership
            for membership in memberships
        }

    async def get_by_user_and_class(self, user_id: int, classroom_id: int) -> ClassMembership | None:
        return self.memberships.get((user_id, classroom_id))


class FakeClassCourseRepository:
    def __init__(self, class_courses: dict[int, ClassCourse]) -> None:
        self.class_courses = class_courses

    async def get_by_id(self, class_course_id: int) -> ClassCourse | None:
        return self.class_courses.get(class_course_id)


class FakeRegistrationRepository:
    def __init__(self, registrations: dict[tuple[int, int], CourseRegistration]) -> None:
        self.session = FakeSession()
        self.registrations = registrations
        self.dropped_registrations: list[CourseRegistration] = []

    async def get_by_membership_and_class_course(
        self,
        membership_id: int,
        class_course_id: int,
    ) -> CourseRegistration | None:
        return self.registrations.get((membership_id, class_course_id))

    async def drop(self, registration: CourseRegistration, dropped_at: datetime) -> CourseRegistration:
        registration.is_active = False
        registration.dropped_at = dropped_at
        self.dropped_registrations.append(registration)
        return registration


def make_membership(membership_id: int, user_id: int, classroom_id: int) -> ClassMembership:
    return ClassMembership(
        id=membership_id,
        user_id=user_id,
        classroom_id=classroom_id,
        role="student",
        status=MEMBERSHIP_STATUS_APPROVED,
    )


def make_class_course(class_course_id: int, classroom_id: int, is_default: bool) -> ClassCourse:
    return ClassCourse(
        id=class_course_id,
        classroom_id=classroom_id,
        course_id=class_course_id,
        is_default=is_default,
        is_active=True,
        created_by_user_id=1,
    )


def make_registration(registration_id: int, membership_id: int, class_course_id: int) -> CourseRegistration:
    return CourseRegistration(
        id=registration_id,
        membership_id=membership_id,
        class_course_id=class_course_id,
        registered_at=datetime.now(timezone.utc),
        dropped_at=None,
        is_active=True,
    )


@pytest.mark.anyio
async def test_default_course_cannot_be_dropped() -> None:
    membership = make_membership(2, user_id=20, classroom_id=1)
    class_course = make_class_course(7, classroom_id=1, is_default=True)
    registration = make_registration(1, membership.id, class_course.id)
    registration_repository = FakeRegistrationRepository(
        {(membership.id, class_course.id): registration}
    )
    service = CourseRegistrationService(
        membership_repository=FakeMembershipRepository([membership]),
        class_course_repository=FakeClassCourseRepository({class_course.id: class_course}),
        registration_repository=registration_repository,
    )

    with pytest.raises(ClassFlowError) as exc_info:
        await service.drop_course(class_course.id, user_id=20)

    assert exc_info.value.status_code == 409
    assert exc_info.value.detail["error_code"] == "DEFAULT_COURSE_DROP_NOT_ALLOWED"
    assert registration.is_active is True
    assert registration_repository.dropped_registrations == []
    assert registration_repository.session.committed is False
