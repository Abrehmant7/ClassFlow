from datetime import UTC, date, datetime, time
from math import ceil

from fastapi import status as http_status

from app.core.exceptions import ClassFlowError
from app.repositories.search import SearchRepository, SearchRow
from app.schemas.search import SearchResponse, SearchResultItem


class SearchService:
    def __init__(self, repository: SearchRepository) -> None:
        self.repository = repository

    async def search(
        self,
        *,
        user_id: int,
        query: str,
        entity_type: str,
        classroom_id: int | None,
        class_course_id: int | None,
        date_from: datetime | date | None,
        date_to: datetime | date | None,
        task_type: str | None,
        priority: str | None,
        status: str | None,
        page: int,
        page_size: int,
    ) -> SearchResponse:
        query = query.strip()
        if not query:
            raise ClassFlowError("Search query cannot be empty", "SEARCH_QUERY_EMPTY", http_status.HTTP_422_UNPROCESSABLE_CONTENT)
        date_from = self._normalize_date(date_from, end_of_day=False)
        date_to = self._normalize_date(date_to, end_of_day=True)
        if date_from is not None and date_to is not None and date_from > date_to:
            raise ClassFlowError("date_from must not be after date_to", "SEARCH_DATE_RANGE_INVALID", http_status.HTTP_422_UNPROCESSABLE_CONTENT)

        await self._validate_filter_access(user_id, classroom_id, class_course_id)
        result = await self.repository.search(
            user_id=user_id,
            query=query,
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
        return SearchResponse(
            items=[self._to_item(row) for row in result.items],
            total=result.total,
            page=page,
            page_size=page_size,
            total_pages=ceil(result.total / page_size) if result.total else 0,
        )

    async def _validate_filter_access(
        self,
        user_id: int,
        classroom_id: int | None,
        class_course_id: int | None,
    ) -> None:
        if classroom_id is not None and not await self.repository.user_can_filter_classroom(user_id, classroom_id):
            raise ClassFlowError("Classroom filter is not authorized", "SEARCH_CLASSROOM_FILTER_NOT_AUTHORIZED", http_status.HTTP_403_FORBIDDEN)
        if class_course_id is not None and not await self.repository.user_can_filter_class_course(
            user_id,
            class_course_id,
            classroom_id,
        ):
            raise ClassFlowError("Course filter is not authorized", "SEARCH_COURSE_FILTER_NOT_AUTHORIZED", http_status.HTTP_403_FORBIDDEN)

    @staticmethod
    def _to_item(row: SearchRow) -> SearchResultItem:
        if row.entity_type == "task":
            action_url = f"/tasks/{row.id}"
        elif row.entity_type == "announcement":
            action_url = f"/classes/{row.classroom_id}?tab=announcements"
        else:
            action_url = f"/classes/{row.classroom_id}?tab=resources&resource={row.id}"
        preview = " ".join(row.preview.split())
        if len(preview) > 240:
            preview = f"{preview[:237].rstrip()}..."
        return SearchResultItem(
            entity_type=row.entity_type,
            id=row.id,
            title=row.title,
            preview=preview,
            classroom_id=row.classroom_id,
            class_course_id=row.class_course_id,
            date=row.date,
            task_type=row.task_type,
            priority=row.priority,
            status=row.status,
            action_url=action_url,
        )

    @staticmethod
    def _normalize_date(value: datetime | date | None, *, end_of_day: bool) -> datetime | None:
        if value is None:
            return None
        if isinstance(value, datetime):
            return value.replace(tzinfo=UTC) if value.tzinfo is None else value
        return datetime.combine(value, time.max if end_of_day else time.min, tzinfo=UTC)
