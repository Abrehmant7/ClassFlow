from typing import Annotated

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.dependencies import get_current_user
from app.database.session import get_db_session
from app.models.user import User
from app.schemas.notification import (
    NotificationEventType,
    NotificationListResponse,
    NotificationMarkAllResponse,
    NotificationRead,
    UnreadNotificationCount,
)
from app.services.notification import NotificationService

router = APIRouter(prefix="/notifications", tags=["notifications"])


@router.get("", response_model=NotificationListResponse)
async def list_notifications(
    current_user: Annotated[User, Depends(get_current_user)],
    session: Annotated[AsyncSession, Depends(get_db_session)],
    unread_only: bool = Query(default=False),
    event_type: NotificationEventType | None = Query(default=None),
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100),
) -> NotificationListResponse:
    return await NotificationService(session).list_notifications(
        current_user.id,
        unread_only=unread_only,
        event_type=event_type,
        page=page,
        page_size=page_size,
    )


@router.get("/unread-count", response_model=UnreadNotificationCount)
async def get_unread_notification_count(
    current_user: Annotated[User, Depends(get_current_user)],
    session: Annotated[AsyncSession, Depends(get_db_session)],
) -> UnreadNotificationCount:
    return await NotificationService(session).count_unread(current_user.id)


@router.patch("/{notification_id}/read", response_model=NotificationRead)
async def mark_notification_read(
    notification_id: int,
    current_user: Annotated[User, Depends(get_current_user)],
    session: Annotated[AsyncSession, Depends(get_db_session)],
) -> NotificationRead:
    return await NotificationService(session).mark_read(notification_id, current_user.id)


@router.patch("/{notification_id}/unread", response_model=NotificationRead)
async def mark_notification_unread(
    notification_id: int,
    current_user: Annotated[User, Depends(get_current_user)],
    session: Annotated[AsyncSession, Depends(get_db_session)],
) -> NotificationRead:
    return await NotificationService(session).mark_unread(notification_id, current_user.id)


@router.post("/read-all", response_model=NotificationMarkAllResponse)
async def mark_all_notifications_read(
    current_user: Annotated[User, Depends(get_current_user)],
    session: Annotated[AsyncSession, Depends(get_db_session)],
) -> NotificationMarkAllResponse:
    count = await NotificationService(session).mark_all_read(current_user.id)
    return NotificationMarkAllResponse(updated_count=count)

