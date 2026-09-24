from datetime import date, datetime
from typing import Annotated

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.dependencies import get_current_user
from app.database.session import get_db_session
from app.models.user import User
from app.repositories.search import SearchRepository
from app.schemas.search import SearchEntityType, SearchResponse
from app.schemas.task import TaskPriority, TaskStatus, TaskType
from app.services.search import SearchService

router = APIRouter(prefix="/search", tags=["search"])


@router.get("", response_model=SearchResponse)
async def global_search(
    current_user: Annotated[User, Depends(get_current_user)],
    session: Annotated[AsyncSession, Depends(get_db_session)],
    q: str = Query(min_length=1, max_length=100),
    entity_type: SearchEntityType = Query(default="all"),
    classroom_id: int | None = Query(default=None, ge=1),
    class_course_id: int | None = Query(default=None, ge=1),
    date_from: datetime | date | None = Query(default=None),
    date_to: datetime | date | None = Query(default=None),
    task_type: TaskType | None = Query(default=None),
    priority: TaskPriority | None = Query(default=None),
    status: TaskStatus | None = Query(default=None),
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100),
) -> SearchResponse:
    return await SearchService(SearchRepository(session)).search(
        user_id=current_user.id,
        query=q,
        entity_type=entity_type,
        classroom_id=classroom_id,
        class_course_id=class_course_id,
        date_from=date_from,
        date_to=date_to,
        task_type=task_type,
        priority=priority,
        status=status,
        page=page,
        page_size=page_size,
    )

