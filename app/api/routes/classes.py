from typing import Annotated

from fastapi import APIRouter, Depends, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.dependencies import get_approved_membership, get_current_user, require_representative
from app.database.session import get_db_session
from app.models.classroom import ClassMembership
from app.models.user import User
from app.repositories.classroom import ClassroomRepository
from app.repositories.membership import ClassMembershipRepository
from app.schemas.classroom import ClassroomCreate, ClassroomMineRead, ClassroomRead, ClassroomUpdate, ClassJoinRequest, ClassMembershipRead
from app.services.classroom import ClassroomService

router = APIRouter(prefix="/classes", tags=["classes"])


def get_classroom_service(session: AsyncSession) -> ClassroomService:
    return ClassroomService(
        classroom_repository=ClassroomRepository(session),
        membership_repository=ClassMembershipRepository(session),
    )


@router.post("", response_model=ClassroomRead, status_code=status.HTTP_201_CREATED)
async def create_classroom(
    classroom_in: ClassroomCreate,
    current_user: Annotated[User, Depends(get_current_user)],
    session: Annotated[AsyncSession, Depends(get_db_session)],
) -> ClassroomRead:
    service = get_classroom_service(session)
    return await service.create_classroom(classroom_in, current_user.id)


@router.get("/mine", response_model=list[ClassroomMineRead])
async def list_my_classrooms(
    current_user: Annotated[User, Depends(get_current_user)],
    session: Annotated[AsyncSession, Depends(get_db_session)],
) -> list[ClassroomMineRead]:
    service = get_classroom_service(session)
    return await service.list_my_classrooms(current_user.id)


@router.get("/{class_id}", response_model=ClassroomRead)
async def read_classroom(
    class_id: int,
    _membership: Annotated[ClassMembership, Depends(get_approved_membership)],
    session: Annotated[AsyncSession, Depends(get_db_session)],
) -> ClassroomRead:
    service = get_classroom_service(session)
    return await service.get_classroom(class_id)


@router.patch("/{class_id}", response_model=ClassroomRead)
async def update_classroom(
    class_id: int,
    classroom_in: ClassroomUpdate,
    _membership: Annotated[ClassMembership, Depends(require_representative)],
    session: Annotated[AsyncSession, Depends(get_db_session)],
) -> ClassroomRead:
    service = get_classroom_service(session)
    return await service.update_classroom(class_id, classroom_in)


@router.post("/{class_id}/join", response_model=ClassMembershipRead, status_code=status.HTTP_201_CREATED)
async def join_classroom(
    class_id: int,
    join_in: ClassJoinRequest,
    current_user: Annotated[User, Depends(get_current_user)],
    session: Annotated[AsyncSession, Depends(get_db_session)],
) -> ClassMembershipRead:
    service = get_classroom_service(session)
    return await service.join_classroom(class_id, current_user.id, join_in)


@router.get("/{class_id}/requests", response_model=list[ClassMembershipRead])
async def list_join_requests(
    class_id: int,
    _membership: Annotated[ClassMembership, Depends(require_representative)],
    session: Annotated[AsyncSession, Depends(get_db_session)],
) -> list[ClassMembershipRead]:
    service = get_classroom_service(session)
    return await service.list_join_requests(class_id)


@router.get("/{class_id}/members", response_model=list[ClassMembershipRead])
async def list_members(
    class_id: int,
    _membership: Annotated[ClassMembership, Depends(get_approved_membership)],
    session: Annotated[AsyncSession, Depends(get_db_session)],
) -> list[ClassMembershipRead]:
    service = get_classroom_service(session)
    return await service.list_members(class_id)