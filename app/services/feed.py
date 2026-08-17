from datetime import UTC, datetime, timedelta, tzinfo
from math import ceil
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

from fastapi import status

from app.core.exceptions import ClassFlowError
from app.models.classroom import CLASS_ROLE_REPRESENTATIVE, ClassMembership
from app.models.task import (
    TASK_PROGRESS_COMPLETED,
    TASK_PROGRESS_PENDING,
    TASK_STATUS_ACTIVE,
    TASK_STATUS_ARCHIVED,
    TASK_STATUS_COMPLETED,
    TASK_VISIBILITY_PERSONAL,
    TASK_VISIBILITY_SHARED,
    Task,
    TaskProgress,
)
from app.repositories.feed import FeedRepository
from app.repositories.membership import ClassMembershipRepository
from app.schemas.feed import (
    FeedDueFilter,
    FeedResponse,
    FeedFilterClassroom,
    FeedFilterCourse,
    FeedFilterOptions,
    FeedSummary,
    FeedTaskClassroom,
    FeedTaskCourse,
    FeedTaskCreator,
    FeedTaskItem,
    FeedTaskPermissions,
    FeedView,
    FeedVisibility,
)


class FeedService:
    def __init__(
        self,
        feed_repository: FeedRepository,
        membership_repository: ClassMembershipRepository,
    ) -> None:
        self.feed_repository = feed_repository
        self.membership_repository = membership_repository

    async def get_personal_feed(
        self,
        user_id: int,
        view: FeedView,
        visibility: FeedVisibility,
        classroom_id: int | None,
        class_course_id: int | None,
        task_type: str | None,
        priority: str | None,
        due: FeedDueFilter | None,
        search: str | None,
        timezone_name: str,
        page: int,
        page_size: int,
    ) -> FeedResponse:
        """Return the authorized global task feed with MVP filters and search."""
        search = self._normalize_search(search)
        timezone = self._parse_timezone(timezone_name)
        now_utc = datetime.now(UTC)
        today_start_utc, today_end_utc, week_end_utc = self._local_due_boundaries(now_utc, timezone)

        await self._validate_filter_access(user_id, classroom_id, class_course_id)

        result = await self.feed_repository.list_personal_feed(
            user_id=user_id,
            view=view,
            visibility=visibility,
            classroom_id=classroom_id,
            class_course_id=class_course_id,
            task_type=task_type,
            priority=priority,
            due=due,
            search=search,
            now_utc=now_utc,
            today_start_utc=today_start_utc,
            today_end_utc=today_end_utc,
            week_end_utc=week_end_utc,
            page=page,
            page_size=page_size,
        )

        membership_cache: dict[int, ClassMembership | None] = {}
        items = []
        for task, progress in result.tasks:
            membership = await self._membership_for_task(user_id, task, membership_cache)
            items.append(
                self._build_feed_item(
                    task=task,
                    progress=progress,
                    membership=membership,
                    user_id=user_id,
                    now_utc=now_utc,
                    today_start_utc=today_start_utc,
                    today_end_utc=today_end_utc,
                    week_end_utc=week_end_utc,
                )
            )

        return FeedResponse(
            items=items,
            page=page,
            page_size=page_size,
            total=result.total,
            total_pages=ceil(result.total / page_size) if result.total else 0,
        )

    async def get_summary(self, user_id: int, timezone_name: str) -> FeedSummary:
        """Return dashboard counts using the same authorization and completion rules as /feed."""
        timezone = self._parse_timezone(timezone_name)
        now_utc = datetime.now(UTC)
        today_start_utc, today_end_utc, upcoming_end_utc = self._local_due_boundaries(now_utc, timezone)
        week_start_utc, week_end_utc = self._local_week_boundaries(now_utc, timezone)

        summary = await self.feed_repository.get_summary(
            user_id=user_id,
            now_utc=now_utc,
            today_start_utc=today_start_utc,
            today_end_utc=today_end_utc,
            week_end_utc=upcoming_end_utc,
            completed_week_start_utc=week_start_utc,
            completed_week_end_utc=week_end_utc,
        )

        return FeedSummary(
            overdue=summary.overdue,
            due_today=summary.due_today,
            upcoming_seven_days=summary.upcoming_seven_days,
            no_deadline=summary.no_deadline,
            completed_this_week=summary.completed_this_week,
        )

    async def get_filter_options(self, user_id: int) -> FeedFilterOptions:
        """Return only active classroom/course filters the user is allowed to select."""
        options = await self.feed_repository.list_filter_options(user_id)
        return FeedFilterOptions(
            classrooms=[
                FeedFilterClassroom(id=classroom.id, name=classroom.name)
                for classroom in options.classrooms
            ],
            courses=[
                FeedFilterCourse(
                    class_course_id=course.class_course_id,
                    classroom_id=course.classroom_id,
                    name=course.name,
                    code=course.code,
                )
                for course in options.courses
            ],
        )

    async def _validate_filter_access(
        self,
        user_id: int,
        classroom_id: int | None,
        class_course_id: int | None,
    ) -> None:
        if classroom_id is not None:
            allowed = await self.feed_repository.user_can_filter_classroom(user_id, classroom_id)
            if not allowed:
                raise ClassFlowError("Classroom filter is not authorized", "FEED_CLASSROOM_FILTER_NOT_AUTHORIZED", status.HTTP_403_FORBIDDEN)

        if class_course_id is not None:
            allowed = await self.feed_repository.user_can_filter_class_course(user_id, class_course_id)
            if not allowed:
                raise ClassFlowError("Course filter is not authorized", "FEED_COURSE_FILTER_NOT_AUTHORIZED", status.HTTP_403_FORBIDDEN)

    async def _membership_for_task(
        self,
        user_id: int,
        task: Task,
        membership_cache: dict[int, ClassMembership | None],
    ) -> ClassMembership | None:
        if task.classroom_id is None:
            return None

        if task.classroom_id not in membership_cache:
            membership_cache[task.classroom_id] = await self.membership_repository.get_by_user_and_class(
                user_id=user_id,
                classroom_id=task.classroom_id,
            )

        return membership_cache[task.classroom_id]

    def _build_feed_item(
        self,
        task: Task,
        progress: TaskProgress | None,
        membership: ClassMembership | None,
        user_id: int,
        now_utc: datetime,
        today_start_utc: datetime,
        today_end_utc: datetime,
        week_end_utc: datetime,
    ) -> FeedTaskItem:
        completion_status = self._completion_status(task, progress)
        completed_at = self._completed_at(task, progress)
        is_overdue = self._is_overdue(task, completion_status, now_utc)
        context_type = self._context_type(task)

        return FeedTaskItem(
            id=task.id,
            title=task.title,
            description=task.description,
            visibility=task.visibility,
            task_type=task.task_type,
            priority=task.priority,
            task_status=task.status,
            my_completion_status=completion_status,
            my_completed_at=completed_at,
            deadline=task.deadline,
            is_overdue=is_overdue,
            due_group=self._due_group(task, completion_status, is_overdue, today_start_utc, today_end_utc, week_end_utc),
            context_type=context_type,
            classroom=self._classroom_context(task),
            course=self._course_context(task),
            creator=self._creator_context(task),
            attachment_count=len(task.attachments),
            permissions=self._permissions(task, membership, user_id),
            created_at=task.created_at,
            updated_at=task.updated_at,
        )

    def _completion_status(self, task: Task, progress: TaskProgress | None) -> str:
        if task.visibility == TASK_VISIBILITY_PERSONAL:
            return TASK_PROGRESS_COMPLETED if task.status == TASK_STATUS_COMPLETED else TASK_PROGRESS_PENDING

        if progress is not None and progress.status == TASK_PROGRESS_COMPLETED:
            return TASK_PROGRESS_COMPLETED

        return TASK_PROGRESS_PENDING

    def _completed_at(self, task: Task, progress: TaskProgress | None) -> datetime | None:
        if task.visibility == TASK_VISIBILITY_PERSONAL:
            return task.completed_at if task.status == TASK_STATUS_COMPLETED else None

        if progress is not None and progress.status == TASK_PROGRESS_COMPLETED:
            return progress.completed_at

        return None

    def _is_overdue(self, task: Task, completion_status: str, now_utc: datetime) -> bool:
        return (
            task.deadline is not None
            and task.deadline < now_utc
            and completion_status == TASK_PROGRESS_PENDING
            and task.status == TASK_STATUS_ACTIVE
        )

    def _due_group(
        self,
        task: Task,
        completion_status: str,
        is_overdue: bool,
        today_start_utc: datetime,
        today_end_utc: datetime,
        week_end_utc: datetime,
    ) -> str:
        if completion_status == TASK_PROGRESS_COMPLETED:
            return "completed"

        if task.deadline is None:
            return "no_deadline"

        if is_overdue:
            return "overdue"

        if today_start_utc <= task.deadline < today_end_utc:
            return "today"

        if today_end_utc <= task.deadline < week_end_utc:
            return "upcoming"

        return "later"

    def _context_type(self, task: Task) -> str:
        if task.classroom_id is None and task.class_course_id is None:
            return "independent"

        if task.class_course_id is not None:
            return "course"

        return "class"

    def _classroom_context(self, task: Task) -> FeedTaskClassroom | None:
        if task.classroom is None:
            return None

        return FeedTaskClassroom(id=task.classroom.id, name=task.classroom.name)

    def _course_context(self, task: Task) -> FeedTaskCourse | None:
        if task.class_course is None or task.class_course.course is None:
            return None

        return FeedTaskCourse(
            class_course_id=task.class_course.id,
            course_id=task.class_course.course_id,
            name=task.class_course.course.name,
            code=task.class_course.course.code,
        )

    def _creator_context(self, task: Task) -> FeedTaskCreator:
        name_parts = [task.creator.first_name, task.creator.last_name]
        name = " ".join(part for part in name_parts if part).strip() or task.creator.username
        return FeedTaskCreator(id=task.creator.id, name=name)

    def _permissions(self, task: Task, membership: ClassMembership | None, user_id: int) -> FeedTaskPermissions:
        is_owner = task.created_by_user_id == user_id
        is_representative = (
            membership is not None
            and membership.role == CLASS_ROLE_REPRESENTATIVE
            and task.visibility == TASK_VISIBILITY_SHARED
        )
        can_update_progress = task.visibility == TASK_VISIBILITY_SHARED and task.status == TASK_STATUS_ACTIVE

        return FeedTaskPermissions(
            can_edit=is_owner if task.visibility == TASK_VISIBILITY_PERSONAL else is_representative,
            can_delete=is_owner and task.visibility == TASK_VISIBILITY_PERSONAL,
            can_manage=is_owner if task.visibility == TASK_VISIBILITY_PERSONAL else is_representative,
            can_update_progress=can_update_progress,
        )

    def _normalize_search(self, search: str | None) -> str | None:
        if search is None:
            return None

        search = search.strip()
        if not search:
            return None

        if len(search) > 100:
            raise ClassFlowError("Search term is too long", "FEED_SEARCH_TOO_LONG", status.HTTP_422_UNPROCESSABLE_CONTENT)

        return search

    def _parse_timezone(self, timezone_name: str) -> tzinfo:
        if timezone_name in {"UTC", "Etc/UTC"}:
            return UTC

        try:
            return ZoneInfo(timezone_name)
        except ZoneInfoNotFoundError:
            raise ClassFlowError("Invalid timezone", "INVALID_TIMEZONE", status.HTTP_422_UNPROCESSABLE_CONTENT)

    def _local_due_boundaries(self, now_utc: datetime, timezone: tzinfo) -> tuple[datetime, datetime, datetime]:
        local_now = now_utc.astimezone(timezone)
        local_start = local_now.replace(hour=0, minute=0, second=0, microsecond=0)
        local_tomorrow = local_start + timedelta(days=1)
        local_week_end = local_tomorrow + timedelta(days=7)

        return (
            local_start.astimezone(UTC),
            local_tomorrow.astimezone(UTC),
            local_week_end.astimezone(UTC),
        )

    def _local_week_boundaries(self, now_utc: datetime, timezone: tzinfo) -> tuple[datetime, datetime]:
        local_now = now_utc.astimezone(timezone)
        local_start = local_now.replace(hour=0, minute=0, second=0, microsecond=0)
        local_week_start = local_start - timedelta(days=local_start.weekday())
        local_next_week_start = local_week_start + timedelta(days=7)

        return (
            local_week_start.astimezone(UTC),
            local_next_week_start.astimezone(UTC),
        )
