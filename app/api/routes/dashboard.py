from typing import Annotated

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.dependencies import get_current_user
from app.database.session import get_db_session
from app.models.user import User
from app.repositories.dashboard import DashboardRepository
from app.repositories.feed import FeedRepository
from app.repositories.membership import ClassMembershipRepository
from app.schemas.dashboard import DashboardResponse
from app.services.dashboard import DashboardService
from app.services.feed import FeedService
from app.services.notification import NotificationService

router = APIRouter(prefix="/dashboard", tags=["dashboard"])


@router.get("", response_model=DashboardResponse)
async def get_dashboard(
    current_user: Annotated[User, Depends(get_current_user)],
    session: Annotated[AsyncSession, Depends(get_db_session)],
    timezone: str = Query(default="UTC", max_length=100),
) -> DashboardResponse:
    service = DashboardService(
        DashboardRepository(session),
        FeedService(
            feed_repository=FeedRepository(session),
            membership_repository=ClassMembershipRepository(session),
        ),
        NotificationService(session),
    )
    return await service.get_dashboard(current_user.id, timezone)

