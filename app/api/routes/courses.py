from typing import Annotated

from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.dependencies import get_current_user
from app.database.session import get_db_session
from app.models.user import User
from app.repositories.course import ClassCourseRepository, CourseRegistrationRepository, CourseRepository
from app.repositories.membership import ClassMembershipRepository
from app.schemas.course import CourseCreate, CourseRead
from app.services.course import CourseService

router = APIRouter(prefix="/courses", tags=["courses"])


def get_course_service(session: AsyncSession) -> CourseService:
    return CourseService(
        course_repository=CourseRepository(session),
        class_course_repository=ClassCourseRepository(session),
        registration_repository=CourseRegistrationRepository(session),
        membership_repository=ClassMembershipRepository(session),
    )


@router.get("", response_model=list[CourseRead])
async def list_courses(
    session: Annotated[AsyncSession, Depends(get_db_session)],
    search: str | None = Query(default=None),
) -> list[CourseRead]:
    service = get_course_service(session)
    return await service.list_courses(search)


@router.get("/{course_id}", response_model=CourseRead)
async def read_course(
    course_id: int,
    session: Annotated[AsyncSession, Depends(get_db_session)],
) -> CourseRead:
    service = get_course_service(session)
    return await service.get_course(course_id)


@router.post("", response_model=CourseRead, status_code=status.HTTP_201_CREATED)
async def create_course(
    course_in: CourseCreate,
    current_user: Annotated[User, Depends(get_current_user)],
    session: Annotated[AsyncSession, Depends(get_db_session)],
) -> CourseRead:
    service = get_course_service(session)
    return await service.create_course(course_in, current_user.id)