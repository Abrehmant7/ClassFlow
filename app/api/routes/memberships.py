from typing import Annotated

from fastapi import APIRouter, Depends, Response, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.dependencies import get_current_user
from app.database.session import get_db_session
from app.models.user import User
from app.repositories.classroom import ClassroomRepository
from app.repositories.membership import ClassMembershipRepository
from app.schemas.classroom import ClassMembershipRead
from app.services.classroom import ClassroomService

router = APIRouter(prefix="/memberships", tags=["memberships"])


def get_classroom_service(session: AsyncSession) -> ClassroomService:
    return ClassroomService(
        classroom_repository=ClassroomRepository(session),
        membership_repository=ClassMembershipRepository(session),
    )


@router.patch("/{membership_id}/approve", response_model=ClassMembershipRead)
async def approve_membership(
    membership_id: int,
    current_user: Annotated[User, Depends(get_current_user)],
    session: Annotated[AsyncSession, Depends(get_db_session)],
) -> ClassMembershipRead:
    service = get_classroom_service(session)
    return await service.approve_membership(membership_id, current_user.id)


@router.patch("/{membership_id}/reject", response_model=ClassMembershipRead)
async def reject_membership(
    membership_id: int,
    current_user: Annotated[User, Depends(get_current_user)],
    session: Annotated[AsyncSession, Depends(get_db_session)],
) -> ClassMembershipRead:
    service = get_classroom_service(session)
    return await service.reject_membership(membership_id, current_user.id)


@router.delete("/{membership_id}", status_code=status.HTTP_204_NO_CONTENT)
async def remove_membership(
    membership_id: int,
    current_user: Annotated[User, Depends(get_current_user)],
    session: Annotated[AsyncSession, Depends(get_db_session)],
) -> Response:
    service = get_classroom_service(session)
    await service.remove_membership(membership_id, current_user.id)
    return Response(status_code=status.HTTP_204_NO_CONTENT)