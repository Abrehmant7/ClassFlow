from datetime import datetime, timezone
import secrets
import string

from fastapi import status
from sqlalchemy.exc import IntegrityError

from app.core.exceptions import ClassFlowError
from app.models.classroom import (
    CLASS_ROLE_REPRESENTATIVE,
    MEMBERSHIP_STATUS_APPROVED,
    CLASS_ROLE_STUDENT,
    MEMBERSHIP_STATUS_PENDING,
    MEMBERSHIP_STATUS_REJECTED,
    MEMBERSHIP_STATUS_REMOVED,
    Classroom,
)
from app.repositories.classroom import ClassroomRepository
from app.repositories.membership import ClassMembershipRepository
from app.schemas.classroom import (
    ClassMembershipRead,
    ClassroomCreate,
    ClassroomMineRead,
    ClassroomRead,
    ClassroomUpdate,
    ClassJoinRequest
)

from app.repositories.course import ClassCourseRepository, CourseRegistrationRepository
from app.services.course import CourseRegistrationService


class ClassroomService:
    def __init__(
        self,
        classroom_repository: ClassroomRepository,
        membership_repository: ClassMembershipRepository,
    ) -> None:
        self.classroom_repository = classroom_repository
        self.membership_repository = membership_repository
        self.session = classroom_repository.session

    async def create_classroom(self, classroom_in: ClassroomCreate, creator_id: int) -> Classroom:
        for _ in range(10):
            join_code = await self._generate_unique_join_code()

            try:
                classroom = await self.classroom_repository.create(
                    classroom_in=classroom_in,
                    creator_id=creator_id,
                    join_code=join_code,
                )
                await self.membership_repository.create(
                    user_id=creator_id,
                    classroom_id=classroom.id,
                    role=CLASS_ROLE_REPRESENTATIVE,
                    status=MEMBERSHIP_STATUS_APPROVED,
                    responded_at=datetime.now(timezone.utc),
                )
                await self.session.commit()
                await self.session.refresh(classroom)
                return classroom
            except IntegrityError:
                await self.session.rollback()

        raise ClassFlowError(
            detail="Could not generate a unique classroom join code",
            error_code="JOIN_CODE_GENERATION_FAILED",
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        )

    async def list_my_classrooms(self, user_id: int) -> list[ClassroomMineRead]:
        rows = await self.classroom_repository.list_for_user(user_id)

        return [
            ClassroomMineRead(
                **ClassroomRead.model_validate(classroom).model_dump(),
                membership=ClassMembershipRead.model_validate(membership),
            )
            for classroom, membership in rows
        ]

    async def get_classroom(self, classroom_id: int) -> Classroom:
        classroom = await self.classroom_repository.get_by_id(classroom_id)

        if classroom is None:
            raise ClassFlowError(
                detail="Classroom not found",
                error_code="CLASSROOM_NOT_FOUND",
                status_code=status.HTTP_404_NOT_FOUND,
            )

        return classroom

    async def update_classroom(self, classroom_id: int, classroom_in: ClassroomUpdate) -> Classroom:
        classroom = await self.classroom_repository.get_by_id(
            classroom_id,
            include_inactive=True,
        )

        if classroom is None:
            raise ClassFlowError(
                detail="Classroom not found",
                error_code="CLASSROOM_NOT_FOUND",
                status_code=status.HTTP_404_NOT_FOUND,
            )

        classroom = await self.classroom_repository.update(classroom, classroom_in)
        await self.session.commit()
        await self.session.refresh(classroom)
        return classroom

    async def _generate_unique_join_code(self) -> str:
        alphabet = string.ascii_uppercase + string.digits

        for _ in range(10):
            join_code = "".join(secrets.choice(alphabet) for _ in range(8))
            existing = await self.classroom_repository.get_by_join_code(join_code)

            if existing is None:
                return join_code

        raise ClassFlowError(
            detail="Could not generate a unique classroom join code",
            error_code="JOIN_CODE_GENERATION_FAILED",
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        )

    async def join_classroom(self, class_id: int, user_id: int, join_in: ClassJoinRequest) -> ClassMembershipRead:
        classroom = await self.classroom_repository.get_by_id(class_id)

        if classroom is None:
            raise ClassFlowError("Classroom not found", "CLASSROOM_NOT_FOUND", status.HTTP_404_NOT_FOUND)

        if classroom.join_code != join_in.join_code.strip().upper():
            raise ClassFlowError("Invalid join code", "INVALID_JOIN_CODE", status.HTTP_403_FORBIDDEN)

        existing = await self.membership_repository.get_by_user_and_class(user_id, class_id)
        now = datetime.now(timezone.utc)

        if existing is not None:
            if existing.status == MEMBERSHIP_STATUS_APPROVED:
                raise ClassFlowError("User is already an approved member", "ALREADY_APPROVED_MEMBER", status.HTTP_409_CONFLICT)
            if existing.status == MEMBERSHIP_STATUS_PENDING:
                raise ClassFlowError("Membership request is already pending", "MEMBERSHIP_REQUEST_ALREADY_PENDING", status.HTTP_409_CONFLICT)

            membership = await self.membership_repository.reset_as_pending_request(existing, now)
        else:
            membership = await self.membership_repository.create(
                user_id=user_id,
                classroom_id=class_id,
                role=CLASS_ROLE_STUDENT,
                status=MEMBERSHIP_STATUS_PENDING,
            )

        await self.session.commit()
        await self.session.refresh(membership)
        return ClassMembershipRead.model_validate(membership)

    async def list_join_requests(self, class_id: int) -> list[ClassMembershipRead]:
        requests = await self.membership_repository.list_pending_for_class(class_id)
        return [ClassMembershipRead.model_validate(request) for request in requests]


    async def list_members(self, class_id: int) -> list[ClassMembershipRead]:
        members = await self.membership_repository.list_approved_for_class(class_id)
        return [ClassMembershipRead.model_validate(member) for member in members]


    async def approve_membership(self, membership_id: int, representative_user_id: int) -> ClassMembershipRead:
        membership = await self._get_membership_or_404(membership_id)
        await self._require_same_class_representative(representative_user_id, membership.classroom_id)

        if membership.status != MEMBERSHIP_STATUS_PENDING:
            raise ClassFlowError("Only pending requests can be approved", "MEMBERSHIP_NOT_PENDING", status.HTTP_409_CONFLICT)

        membership = await self.membership_repository.update_status(
            membership,
            MEMBERSHIP_STATUS_APPROVED,
            datetime.now(timezone.utc),
        )
        
        registration_service = CourseRegistrationService(
        membership_repository=self.membership_repository,
        class_course_repository=ClassCourseRepository(self.session),
        registration_repository=CourseRegistrationRepository(self.session),
        )

        await registration_service.register_default_courses(membership)
        await self.session.commit()
        await self.session.refresh(membership)
        return ClassMembershipRead.model_validate(membership)


    async def reject_membership(self, membership_id: int, representative_user_id: int) -> ClassMembershipRead:
        membership = await self._get_membership_or_404(membership_id)
        await self._require_same_class_representative(representative_user_id, membership.classroom_id)

        if membership.status != MEMBERSHIP_STATUS_PENDING:
            raise ClassFlowError("Only pending requests can be rejected", "MEMBERSHIP_NOT_PENDING", status.HTTP_409_CONFLICT)

        membership = await self.membership_repository.update_status(
            membership,
            MEMBERSHIP_STATUS_REJECTED,
            datetime.now(timezone.utc),
        )
        await self.session.commit()
        await self.session.refresh(membership)
        return ClassMembershipRead.model_validate(membership)


    async def remove_membership(self, membership_id: int, representative_user_id: int) -> None:
        membership = await self._get_membership_or_404(membership_id)
        await self._require_same_class_representative(representative_user_id, membership.classroom_id)

        classroom = await self.classroom_repository.get_by_id(membership.classroom_id, include_inactive=True)
        if classroom is not None and membership.user_id == classroom.creator_id:
            raise ClassFlowError("Class creator cannot be removed", "CANNOT_REMOVE_CLASS_CREATOR", status.HTTP_409_CONFLICT)

        await self.membership_repository.update_status(
            membership,
            MEMBERSHIP_STATUS_REMOVED,
            datetime.now(timezone.utc),
        )
        await self.session.commit()


    async def _get_membership_or_404(self, membership_id: int):
        membership = await self.membership_repository.get_by_id(membership_id)
        if membership is None:
            raise ClassFlowError("Membership not found", "MEMBERSHIP_NOT_FOUND", status.HTTP_404_NOT_FOUND)
        return membership


    async def _require_same_class_representative(self, user_id: int, classroom_id: int):
        representative = await self.membership_repository.get_by_user_and_class(user_id, classroom_id)

        if (
            representative is None
            or representative.status != MEMBERSHIP_STATUS_APPROVED
            or representative.role != CLASS_ROLE_REPRESENTATIVE
        ):
            raise ClassFlowError("Class representative access required", "CLASS_REPRESENTATIVE_REQUIRED", status.HTTP_403_FORBIDDEN)

        return representative