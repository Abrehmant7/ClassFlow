from sqlalchemy import exists, or_, select
from sqlalchemy.orm import aliased

from app.models.classroom import CLASS_ROLE_REPRESENTATIVE, MEMBERSHIP_STATUS_APPROVED, ClassMembership, Classroom
from app.models.course import ClassCourse, CourseRegistration


def accessible_class_content(model, user_id: int):
    """Apply class membership and course scope before selecting any content."""
    membership = aliased(ClassMembership)
    classroom = aliased(Classroom)
    course = aliased(ClassCourse)
    registration = aliased(CourseRegistration)
    registered = exists(
        select(registration.id).where(
            registration.membership_id == membership.id,
            registration.class_course_id == course.id,
            registration.is_active.is_(True),
        ).correlate(membership, course)
    )
    course_access = exists(
        select(course.id).where(
            course.id == model.class_course_id,
            course.classroom_id == model.classroom_id,
            course.is_active.is_(True),
            or_(membership.role == CLASS_ROLE_REPRESENTATIVE, registered),
        ).correlate(model, membership)
    )
    return exists(
        select(membership.id)
        .join(classroom, classroom.id == membership.classroom_id)
        .where(
            membership.user_id == user_id,
            membership.classroom_id == model.classroom_id,
            membership.status == MEMBERSHIP_STATUS_APPROVED,
            classroom.is_active.is_(True),
            or_(model.class_course_id.is_(None), course_access),
        )
        .correlate(model)
    )
