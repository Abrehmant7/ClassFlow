from typing import Annotated

from fastapi import APIRouter, Depends, Query, Response, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.dependencies import get_approved_membership, get_current_user, require_representative
from app.database.session import get_db_session
from app.models.classroom import ClassMembership
from app.models.user import User
from app.repositories.course import ClassCourseRepository, CourseRegistrationRepository, CourseRepository
from app.repositories.membership import ClassMembershipRepository
from app.schemas.course import ClassCourseCreate, ClassCourseRead, ClassCourseUpdate, CourseRegistrationRead
from app.services.course import CourseRegistrationService, CourseService

router = APIRouter(tags=["class-courses"])


def get_course_service(session: AsyncSession) -> CourseService:
    return CourseService(
        course_repository=CourseRepository(session),
        class_course_repository=ClassCourseRepository(session),
        registration_repository=CourseRegistrationRepository(session),
        membership_repository=ClassMembershipRepository(session),
    )


def get_registration_service(session: AsyncSession) -> CourseRegistrationService:
    return CourseRegistrationService(
        membership_repository=ClassMembershipRepository(session),
        class_course_repository=ClassCourseRepository(session),
        registration_repository=CourseRegistrationRepository(session),
    )


@router.post("/classes/{class_id}/courses", response_model=ClassCourseRead, status_code=status.HTTP_201_CREATED)
async def add_class_course(
    class_id: int,
    class_course_in: ClassCourseCreate,
    current_user: Annotated[User, Depends(get_current_user)],
    _membership: Annotated[ClassMembership, Depends(require_representative)],
    session: Annotated[AsyncSession, Depends(get_db_session)],
) -> ClassCourseRead:
    service = get_course_service(session)
    return await service.add_class_course(class_id, class_course_in, current_user.id)


@router.get("/classes/{class_id}/courses", response_model=list[ClassCourseRead])
async def list_class_courses(
    class_id: int,
    _membership: Annotated[ClassMembership, Depends(get_approved_membership)],
    session: Annotated[AsyncSession, Depends(get_db_session)],
    include_inactive: bool = Query(default=False),
) -> list[ClassCourseRead]:
    service = get_course_service(session)
    return await service.list_class_courses(class_id, include_inactive)


@router.patch("/class-courses/{class_course_id}", response_model=ClassCourseRead)
async def update_class_course(
    class_course_id: int,
    class_course_in: ClassCourseUpdate,
    current_user: Annotated[User, Depends(get_current_user)],
    session: Annotated[AsyncSession, Depends(get_db_session)],
) -> ClassCourseRead:
    service = get_course_service(session)
    return await service.update_class_course(class_course_id, class_course_in, current_user.id)


@router.delete("/class-courses/{class_course_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_class_course(
    class_course_id: int,
    current_user: Annotated[User, Depends(get_current_user)],
    session: Annotated[AsyncSession, Depends(get_db_session)],
) -> Response:
    service = get_course_service(session)
    await service.delete_class_course(class_course_id, current_user.id)
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.post("/class-courses/{class_course_id}/register", response_model=CourseRegistrationRead, status_code=status.HTTP_201_CREATED)
async def register_course(
    class_course_id: int,
    current_user: Annotated[User, Depends(get_current_user)],
    session: Annotated[AsyncSession, Depends(get_db_session)],
) -> CourseRegistrationRead:
    service = get_registration_service(session)
    return await service.register_optional_course(class_course_id, current_user.id)


@router.delete("/class-courses/{class_course_id}/register", status_code=status.HTTP_204_NO_CONTENT)
async def drop_course(
    class_course_id: int,
    current_user: Annotated[User, Depends(get_current_user)],
    session: Annotated[AsyncSession, Depends(get_db_session)],
) -> Response:
    service = get_registration_service(session)
    await service.drop_course(class_course_id, current_user.id)
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.get("/classes/{class_id}/my-courses", response_model=list[CourseRegistrationRead])
async def list_my_courses(
    class_id: int,
    current_user: Annotated[User, Depends(get_current_user)],
    _membership: Annotated[ClassMembership, Depends(get_approved_membership)],
    session: Annotated[AsyncSession, Depends(get_db_session)],
) -> list[CourseRegistrationRead]:
    service = get_registration_service(session)
    return await service.list_my_courses(class_id, current_user.id)