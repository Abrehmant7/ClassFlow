from datetime import datetime
from typing import NamedTuple

from sqlalchemy import DateTime, Integer, String, func, literal, or_, select, union_all

from app.models.announcement import Announcement
from app.models.resource import Resource
from app.models.task import Task
from app.repositories.audience import (
    active_course_access_condition,
    approved_class_access_condition,
    task_access_condition,
)
from app.repositories.base import BaseRepository
from app.repositories.content_access import accessible_class_content


class SearchRow(NamedTuple):
    entity_type: str
    id: int
    title: str
    preview: str
    classroom_id: int | None
    class_course_id: int | None
    date: datetime | None
    task_type: str | None
    priority: str | None
    status: str | None


class SearchQueryResult(NamedTuple):
    items: list[SearchRow]
    total: int


class SearchRepository(BaseRepository[Task]):
    async def search(
        self,
        *,
        user_id: int,
        query: str,
        entity_type: str,
        classroom_id: int | None,
        class_course_id: int | None,
        date_from: datetime | None,
        date_to: datetime | None,
        task_type: str | None,
        priority: str | None,
        status: str | None,
        page: int,
        page_size: int,
    ) -> SearchQueryResult:
        pattern = f"%{self._escape_like(query)}%"
        statements = []

        if entity_type in {"all", "task"}:
            statements.append(
                self._task_search(
                    user_id,
                    pattern,
                    classroom_id,
                    class_course_id,
                    date_from,
                    date_to,
                    task_type,
                    priority,
                    status,
                )
            )

        task_filters_active = any(value is not None for value in (task_type, priority, status))
        if not task_filters_active and entity_type in {"all", "announcement"}:
            statements.append(
                self._announcement_search(
                    user_id,
                    pattern,
                    classroom_id,
                    class_course_id,
                    date_from,
                    date_to,
                )
            )
        if not task_filters_active and entity_type in {"all", "resource"}:
            statements.append(
                self._resource_search(
                    user_id,
                    pattern,
                    classroom_id,
                    class_course_id,
                    date_from,
                    date_to,
                )
            )

        combined = union_all(*statements).subquery("authorized_search")
        total = int(await self.session.scalar(select(func.count()).select_from(combined)) or 0)
        result = await self.session.execute(
            select(combined)
            .order_by(combined.c.date.desc().nulls_last(), combined.c.entity_type.asc(), combined.c.id.desc())
            .offset((page - 1) * page_size)
            .limit(page_size)
        )
        return SearchQueryResult(
            items=[SearchRow(**dict(row)) for row in result.mappings().all()],
            total=total,
        )

    async def user_can_filter_classroom(self, user_id: int, classroom_id: int) -> bool:
        result = await self.session.scalar(
            select(literal(1))
            .where(approved_class_access_condition(user_id, classroom_id))
            .limit(1)
        )
        return result is not None

    async def user_can_filter_class_course(
        self,
        user_id: int,
        class_course_id: int,
        classroom_id: int | None = None,
    ) -> bool:
        from app.models.course import ClassCourse

        conditions = [
            ClassCourse.id == class_course_id,
            ClassCourse.is_active.is_(True),
            active_course_access_condition(user_id, ClassCourse.classroom_id, ClassCourse.id),
        ]
        if classroom_id is not None:
            conditions.append(ClassCourse.classroom_id == classroom_id)
        result = await self.session.scalar(select(ClassCourse.id).where(*conditions).limit(1))
        return result is not None

    def _task_search(
        self,
        user_id: int,
        pattern: str,
        classroom_id: int | None,
        class_course_id: int | None,
        date_from: datetime | None,
        date_to: datetime | None,
        task_type: str | None,
        priority: str | None,
        status: str | None,
    ):
        statement = select(
            literal("task", type_=String()).label("entity_type"),
            Task.id.label("id"),
            Task.title.label("title"),
            func.coalesce(Task.description, "").label("preview"),
            Task.classroom_id.label("classroom_id"),
            Task.class_course_id.label("class_course_id"),
            Task.deadline.label("date"),
            Task.task_type.label("task_type"),
            Task.priority.label("priority"),
            Task.status.label("status"),
        ).where(
            task_access_condition(user_id),
            or_(
                Task.title.ilike(pattern, escape="\\"),
                Task.description.ilike(pattern, escape="\\"),
            ),
        )
        return self._apply_filters(
            statement,
            Task,
            Task.deadline,
            classroom_id,
            class_course_id,
            date_from,
            date_to,
            task_type=task_type,
            priority=priority,
            status=status,
        )

    def _announcement_search(
        self,
        user_id: int,
        pattern: str,
        classroom_id: int | None,
        class_course_id: int | None,
        date_from: datetime | None,
        date_to: datetime | None,
    ):
        statement = select(
            literal("announcement", type_=String()).label("entity_type"),
            Announcement.id.label("id"),
            Announcement.title.label("title"),
            Announcement.body.label("preview"),
            Announcement.classroom_id.label("classroom_id"),
            Announcement.class_course_id.label("class_course_id"),
            Announcement.created_at.label("date"),
            literal(None, type_=String()).label("task_type"),
            literal(None, type_=String()).label("priority"),
            literal(None, type_=String()).label("status"),
        ).where(
            accessible_class_content(Announcement, user_id),
            or_(
                Announcement.title.ilike(pattern, escape="\\"),
                Announcement.body.ilike(pattern, escape="\\"),
            ),
        )
        return self._apply_filters(
            statement,
            Announcement,
            Announcement.created_at,
            classroom_id,
            class_course_id,
            date_from,
            date_to,
        )

    def _resource_search(
        self,
        user_id: int,
        pattern: str,
        classroom_id: int | None,
        class_course_id: int | None,
        date_from: datetime | None,
        date_to: datetime | None,
    ):
        statement = select(
            literal("resource", type_=String()).label("entity_type"),
            Resource.id.label("id"),
            Resource.title.label("title"),
            func.coalesce(Resource.description, "").label("preview"),
            Resource.classroom_id.label("classroom_id"),
            Resource.class_course_id.label("class_course_id"),
            Resource.created_at.label("date"),
            literal(None, type_=String()).label("task_type"),
            literal(None, type_=String()).label("priority"),
            literal(None, type_=String()).label("status"),
        ).where(
            Resource.is_enabled.is_(True),
            accessible_class_content(Resource, user_id),
            or_(
                Resource.title.ilike(pattern, escape="\\"),
                Resource.description.ilike(pattern, escape="\\"),
            ),
        )
        return self._apply_filters(
            statement,
            Resource,
            Resource.created_at,
            classroom_id,
            class_course_id,
            date_from,
            date_to,
        )

    @staticmethod
    def _apply_filters(
        statement,
        model,
        date_column,
        classroom_id: int | None,
        class_course_id: int | None,
        date_from: datetime | None,
        date_to: datetime | None,
        *,
        task_type: str | None = None,
        priority: str | None = None,
        status: str | None = None,
    ):
        if classroom_id is not None:
            statement = statement.where(model.classroom_id == classroom_id)
        if class_course_id is not None:
            statement = statement.where(model.class_course_id == class_course_id)
        if date_from is not None:
            statement = statement.where(date_column >= date_from)
        if date_to is not None:
            statement = statement.where(date_column <= date_to)
        if task_type is not None:
            statement = statement.where(Task.task_type == task_type)
        if priority is not None:
            statement = statement.where(Task.priority == priority)
        if status is not None:
            statement = statement.where(Task.status == status)
        return statement

    @staticmethod
    def _escape_like(value: str) -> str:
        return value.replace("\\", "\\\\").replace("%", "\\%").replace("_", "\\_")
