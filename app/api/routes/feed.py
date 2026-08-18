from typing import Annotated

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.dependencies import get_current_user
from app.database.session import get_db_session
from app.models.user import User
from app.repositories.feed import FeedRepository
from app.repositories.membership import ClassMembershipRepository
from app.schemas.feed import FeedDueFilter, FeedFilterOptions, FeedResponse, FeedSummary, FeedView, FeedVisibility
from app.schemas.task import TaskPriority, TaskType
from app.services.feed import FeedService

router = APIRouter(prefix="/feed", tags=["feed"])


def get_feed_service(session: AsyncSession) -> FeedService:
    return FeedService(
        feed_repository=FeedRepository(session),
        membership_repository=ClassMembershipRepository(session),
    )


@router.get("", response_model=FeedResponse)
async def read_feed(
    current_user: Annotated[User, Depends(get_current_user)],
    session: Annotated[AsyncSession, Depends(get_db_session)],
    view: FeedView = Query(default="active"),
    visibility: FeedVisibility = Query(default="all"),
    classroom_id: int | None = Query(default=None, ge=1),
    class_course_id: int | None = Query(default=None, ge=1),
    task_type: TaskType | None = Query(default=None),
    priority: TaskPriority | None = Query(default=None),
    due: FeedDueFilter | None = Query(default=None),
    search: str | None = Query(default=None, max_length=100),
    timezone: str = Query(default="UTC"),
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100),
) -> FeedResponse:
    service = get_feed_service(session)
    return await service.get_personal_feed(
        user_id=current_user.id,
        view=view,
        visibility=visibility,
        classroom_id=classroom_id,
        class_course_id=class_course_id,
        task_type=task_type,
        priority=priority,
        due=due,
        search=search,
        timezone_name=timezone,
        page=page,
        page_size=page_size,
    )


@router.get("/summary", response_model=FeedSummary)
async def read_feed_summary(
    current_user: Annotated[User, Depends(get_current_user)],
    session: Annotated[AsyncSession, Depends(get_db_session)],
    timezone: str = Query(default="UTC"),
) -> FeedSummary:
    service = get_feed_service(session)
    return await service.get_summary(current_user.id, timezone)


@router.get("/filter-options", response_model=FeedFilterOptions)
async def read_feed_filter_options(
    current_user: Annotated[User, Depends(get_current_user)],
    session: Annotated[AsyncSession, Depends(get_db_session)],
) -> FeedFilterOptions:
    service = get_feed_service(session)
    return await service.get_filter_options(current_user.id)
