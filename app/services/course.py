from datetime import datetime, timezone

from fastapi import status
from sqlalchemy.exc import IntegrityError

from app.core.exceptions import ClassFlowError
from app.models.classroom import MEMBERSHIP_STATUS_APPROVED
from app.models.course import ClassCourse
from app.repositories.course import ClassCourseRepository, CourseRegistrationRepository, CourseRepository
from app.repositories.membership import ClassMembershipRepository
from app.schemas.course import (
    ClassCourseCreate,
    ClassCourseRead,
    ClassCourseUpdate,
    CourseCreate,
    CourseRead,
    CourseRegistrationRead,
)


class CourseService:
    def __init__(
        self,
        course_repository: CourseRepository,
        class_course_repository: ClassCourseRepository,
        registration_repository: CourseRegistrationRepository,
        membership_repository: ClassMembershipRepository,
    ) -> None:
        self.course_repository = course_repository
        self.class_course_repository = class_course_repository
        self.registration_repository = registration_repository
        self.membership_repository = membership_repository
        self.session = course_repository.session

    async def list_courses(self, search: str | None = None) -> list[CourseRead]:
        courses = await self.course_repository.list(search)
        return [CourseRead.model_validate(course) for course in courses]

    async def get_course(self, course_id: int) -> CourseRead:
        course = await self.course_repository.get_by_id(course_id)

        if course is None:
            raise ClassFlowError("Course not found", "COURSE_NOT_FOUND", status.HTTP_404_NOT_FOUND)

        return CourseRead.model_validate(course)

    async def create_course(self, course_in: CourseCreate, user_id: int) -> CourseRead:
        is_representative = await self.membership_repository.has_approved_representative_membership(user_id)

        if not is_representative:
            raise ClassFlowError("Approved representative access required", "REPRESENTATIVE_REQUIRED", status.HTTP_403_FORBIDDEN)

        name = self.normalize_name(course_in.name)
        code = self.normalize_code(course_in.code)

        existing_by_code = await self.course_repository.get_by_code(code)
        if existing_by_code is not None:
            raise ClassFlowError("Course code already exists", "COURSE_CODE_ALREADY_EXISTS", status.HTTP_409_CONFLICT)

        existing_by_name = await self.course_repository.get_by_normalized_name(name)
        if existing_by_name is not None:
            raise ClassFlowError("Course name already exists", "COURSE_NAME_ALREADY_EXISTS", status.HTTP_409_CONFLICT)

        try:
            course = await self.course_repository.create(
                name=name,
                code=code,
                description=course_in.description,
            )
            await self.session.commit()
            await self.session.refresh(course)
            return CourseRead.model_validate(course)
        except IntegrityError:
            await self.session.rollback()
            raise ClassFlowError("Course already exists", "COURSE_ALREADY_EXISTS", status.HTTP_409_CONFLICT)

    async def add_class_course(self, classroom_id: int, class_course_in: ClassCourseCreate, user_id: int) -> ClassCourseRead:
        course = await self.course_repository.get_by_id(class_course_in.course_id)

        if course is None:
            raise ClassFlowError("Course not found", "COURSE_NOT_FOUND", status.HTTP_404_NOT_FOUND)

        existing = await self.class_course_repository.get_by_class_and_course(
            classroom_id=classroom_id,
            course_id=class_course_in.course_id,
        )

        if existing is not None:
            if existing.is_active:
                raise ClassFlowError("Course is already added to this class", "CLASS_COURSE_ALREADY_EXISTS", status.HTTP_409_CONFLICT)

            existing.instructor_name = class_course_in.instructor_name
            existing.is_default = class_course_in.is_default
            existing.is_active = True
            class_course = existing
            await self.session.flush()
        else:
            class_course = await self.class_course_repository.create(
                classroom_id=classroom_id,
                class_course_in=class_course_in,
                created_by_user_id=user_id,
            )

        if class_course.is_default and class_course.is_active:
            registration_service = CourseRegistrationService(
                membership_repository=self.membership_repository,
                class_course_repository=self.class_course_repository,
                registration_repository=self.registration_repository,
            )
            await registration_service.register_existing_approved_members_for_default_course(class_course)

        await self.session.commit()
        class_course = await self.class_course_repository.get_by_id(class_course.id)
        return ClassCourseRead.model_validate(class_course)

    async def list_class_courses(self, classroom_id: int, include_inactive: bool = False) -> list[ClassCourseRead]:
        class_courses = await self.class_course_repository.list_for_class(classroom_id, include_inactive)
        return [ClassCourseRead.model_validate(class_course) for class_course in class_courses]

    async def update_class_course(self, class_course_id: int, class_course_in: ClassCourseUpdate, user_id: int) -> ClassCourseRead:
        class_course = await self._get_class_course_or_404(class_course_id)
        await self._require_same_class_representative(user_id, class_course.classroom_id)

        class_course = await self.class_course_repository.update(class_course, class_course_in)

        if class_course.is_active and class_course.is_default:
            registration_service = CourseRegistrationService(
                membership_repository=self.membership_repository,
                class_course_repository=self.class_course_repository,
                registration_repository=self.registration_repository,
            )
            await registration_service.register_existing_approved_members_for_default_course(class_course)

        await self.session.commit()
        class_course = await self.class_course_repository.get_by_id(class_course.id)
        return ClassCourseRead.model_validate(class_course)

    async def delete_class_course(self, class_course_id: int, user_id: int) -> None:
        class_course = await self._get_class_course_or_404(class_course_id)
        await self._require_same_class_representative(user_id, class_course.classroom_id)

        await self.class_course_repository.deactivate(class_course)
        await self.session.commit()

    async def _get_class_course_or_404(self, class_course_id: int) -> ClassCourse:
        class_course = await self.class_course_repository.get_by_id(class_course_id)

        if class_course is None:
            raise ClassFlowError("Class course not found", "CLASS_COURSE_NOT_FOUND", status.HTTP_404_NOT_FOUND)

        return class_course

    async def _require_same_class_representative(self, user_id: int, classroom_id: int):
        membership = await self.membership_repository.get_by_user_and_class(user_id, classroom_id)

        if membership is None or membership.status != "approved" or membership.role != "representative":
            raise ClassFlowError("Class representative access required", "CLASS_REPRESENTATIVE_REQUIRED", status.HTTP_403_FORBIDDEN)

        return membership

    @staticmethod
    def normalize_code(code: str) -> str:
        return code.strip().upper()

    @staticmethod
    def normalize_name(name: str) -> str:
        return " ".join(name.strip().split())


class CourseRegistrationService:
    def __init__(
        self,
        membership_repository: ClassMembershipRepository,
        class_course_repository: ClassCourseRepository,
        registration_repository: CourseRegistrationRepository,
    ) -> None:
        self.membership_repository = membership_repository
        self.class_course_repository = class_course_repository
        self.registration_repository = registration_repository
        self.session = registration_repository.session

    async def register_default_courses(self, membership) -> None:
        class_courses = await self.class_course_repository.list_active_default_for_class(membership.classroom_id)

        for class_course in class_courses:
            await self._activate_or_create_registration(
                membership_id=membership.id,
                class_course_id=class_course.id,
            )

    async def register_existing_approved_members_for_default_course(self, class_course: ClassCourse) -> None:
        if not class_course.is_active or not class_course.is_default:
            return

        memberships = await self.membership_repository.list_approved_for_class(class_course.classroom_id)

        for membership in memberships:
            await self._activate_or_create_registration(
                membership_id=membership.id,
                class_course_id=class_course.id,
            )

    async def register_optional_course(self, class_course_id: int, user_id: int) -> CourseRegistrationRead:
        class_course = await self._get_active_class_course_or_404(class_course_id)
        membership = await self._get_approved_membership_for_class(user_id, class_course.classroom_id)

        registration = await self._activate_or_create_registration(
            membership_id=membership.id,
            class_course_id=class_course.id,
            fail_if_active=True,
        )

        await self.session.commit()
        registration = await self.registration_repository.get_by_membership_and_class_course(membership.id, class_course.id)
        return CourseRegistrationRead.model_validate(registration)

    async def drop_course(self, class_course_id: int, user_id: int) -> None:
        class_course = await self._get_active_class_course_or_404(class_course_id)
        membership = await self._get_approved_membership_for_class(user_id, class_course.classroom_id)
        registration = await self.registration_repository.get_by_membership_and_class_course(
            membership_id=membership.id,
            class_course_id=class_course.id,
        )

        if registration is None or not registration.is_active:
            raise ClassFlowError("Active course registration not found", "COURSE_REGISTRATION_NOT_FOUND", status.HTTP_404_NOT_FOUND)

        await self.registration_repository.drop(registration, datetime.now(timezone.utc))
        await self.session.commit()

    async def list_my_courses(self, class_id: int, user_id: int) -> list[CourseRegistrationRead]:
        membership = await self._get_approved_membership_for_class(user_id, class_id)
        registrations = await self.registration_repository.list_active_for_membership(membership.id)
        return [CourseRegistrationRead.model_validate(registration) for registration in registrations]

    async def _activate_or_create_registration(
        self,
        membership_id: int,
        class_course_id: int,
        fail_if_active: bool = False,
    ):
        existing = await self.registration_repository.get_by_membership_and_class_course(
            membership_id=membership_id,
            class_course_id=class_course_id,
        )

        if existing is not None:
            if existing.is_active and fail_if_active:
                raise ClassFlowError("Course is already registered", "COURSE_ALREADY_REGISTERED", status.HTTP_409_CONFLICT)

            if existing.is_active:
                return existing

            return await self.registration_repository.reactivate(existing, datetime.now(timezone.utc))

        return await self.registration_repository.create(
            membership_id=membership_id,
            class_course_id=class_course_id,
        )

    async def _get_active_class_course_or_404(self, class_course_id: int) -> ClassCourse:
        class_course = await self.class_course_repository.get_by_id(class_course_id)

        if class_course is None or not class_course.is_active:
            raise ClassFlowError("Class course not found", "CLASS_COURSE_NOT_FOUND", status.HTTP_404_NOT_FOUND)

        return class_course

    async def _get_approved_membership_for_class(self, user_id: int, classroom_id: int):
        membership = await self.membership_repository.get_by_user_and_class(user_id, classroom_id)

        if membership is None or membership.status != MEMBERSHIP_STATUS_APPROVED:
            raise ClassFlowError("Approved class membership required", "APPROVED_CLASS_MEMBERSHIP_REQUIRED", status.HTTP_403_FORBIDDEN)

        return membership