from typing import Annotated

from fastapi import APIRouter, Depends, Response, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.dependencies import get_current_user
from app.database.session import get_db_session
from app.models.user import User
from app.schemas.announcement import AnnouncementCreate, AnnouncementRead, AnnouncementUpdate
from app.services.announcement import AnnouncementService

router = APIRouter(tags=["announcements"])


@router.post("/classes/{class_id}/announcements", response_model=AnnouncementRead, status_code=status.HTTP_201_CREATED)
async def create_announcement(
    class_id: int,
    announcement_in: AnnouncementCreate,
    current_user: Annotated[User, Depends(get_current_user)],
    session: Annotated[AsyncSession, Depends(get_db_session)],
) -> AnnouncementRead:
    return await AnnouncementService(session).create_announcement(class_id, announcement_in, current_user.id)


@router.get("/classes/{class_id}/announcements", response_model=list[AnnouncementRead])
async def list_announcements(
    class_id: int,
    current_user: Annotated[User, Depends(get_current_user)],
    session: Annotated[AsyncSession, Depends(get_db_session)],
) -> list[AnnouncementRead]:
    return await AnnouncementService(session).list_announcements(class_id, current_user.id)


@router.get("/announcements/{announcement_id}", response_model=AnnouncementRead)
async def read_announcement(
    announcement_id: int,
    current_user: Annotated[User, Depends(get_current_user)],
    session: Annotated[AsyncSession, Depends(get_db_session)],
) -> AnnouncementRead:
    return await AnnouncementService(session).get_announcement(announcement_id, current_user.id)


@router.patch("/announcements/{announcement_id}", response_model=AnnouncementRead)
async def update_announcement(
    announcement_id: int,
    announcement_in: AnnouncementUpdate,
    current_user: Annotated[User, Depends(get_current_user)],
    session: Annotated[AsyncSession, Depends(get_db_session)],
) -> AnnouncementRead:
    return await AnnouncementService(session).update_announcement(announcement_id, announcement_in, current_user.id)


@router.delete("/announcements/{announcement_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_announcement(
    announcement_id: int,
    current_user: Annotated[User, Depends(get_current_user)],
    session: Annotated[AsyncSession, Depends(get_db_session)],
) -> Response:
    await AnnouncementService(session).delete_announcement(announcement_id, current_user.id)
    return Response(status_code=status.HTTP_204_NO_CONTENT)

