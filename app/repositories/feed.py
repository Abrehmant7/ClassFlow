from datetime import datetime
from typing import NamedTuple

from sqlalchemy import Select, and_, case, func, or_, select
from sqlalchemy.orm import selectinload

from app.models.classroom import MEMBERSHIP_STATUS_APPROVED, ClassMembership, Classroom
from app.models.course import ClassCourse, Course, CourseRegistration
from app.models.task import (
    TASK_PROGRESS_COMPLETED,
    TASK_STATUS_ACTIVE,
    TASK_STATUS_ARCHIVED,
    TASK_STATUS_COMPLETED,
    TASK_VISIBILITY_PERSONAL,
    TASK_VISIBILITY_SHARED,
    Task,
    TaskProgress,
)
from app.repositories.base import BaseRepository
from app.schemas.feed import FeedDueFilter, FeedView, FeedVisibility


class FeedQueryResult(NamedTuple):
    tasks: list[tuple[Task, TaskProgress | None]]
    total: int


class FeedSummaryResult(NamedTuple):
    overdue: int
    due_today: int
    upcoming_seven_days: int
    no_deadline: int
    completed_this_week: int


class FeedFilterClassroomRow(NamedTuple):
    id: int
    name: str


class FeedFilterCourseRow(NamedTuple):
    class_course_id: int
    classroom_id: int
    name: str
    code: str


class FeedFilterOptionsResult(NamedTuple):
    classrooms: list[FeedFilterClassroomRow]
    courses: list[FeedFilterCourseRow]


class FeedRepository(BaseRepository[Task]):
    async def list_personal_feed(
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
        now_utc: datetime,
        today_start_utc: datetime,
        today_end_utc: datetime,
        week_end_utc: datetime,
        page: int,
        page_size: int,
    ) -> FeedQueryResult:
        progress_join = self._progress_join_for_user(user_id)
        statement = (
            select(Task, TaskProgress)
            .outerjoin(TaskProgress, progress_join)
            .outerjoin(Classroom, Classroom.id == Task.classroom_id)
            .outerjoin(ClassCourse, ClassCourse.id == Task.class_course_id)
            .outerjoin(Course, Course.id == ClassCourse.course_id)
            .options(
                selectinload(Task.creator),
                selectinload(Task.attachments),
                selectinload(Task.classroom),
                selectinload(Task.class_course).selectinload(ClassCourse.course),
            )
            .where(self._authorized_feed_condition(user_id))
        )

        statement = self._apply_view_filter(statement, view)
        statement = self._apply_optional_filters(statement, visibility, classroom_id, class_course_id, task_type, priority)
        statement = self._apply_due_filter(statement, due, now_utc, today_start_utc, today_end_utc, week_end_utc)
        statement = self._apply_search_filter(statement, search)

        total_statement = select(func.count(func.distinct(Task.id))).select_from(Task)
        total_statement = total_statement.outerjoin(TaskProgress, progress_join)
        total_statement = total_statement.outerjoin(Classroom, Classroom.id == Task.classroom_id)
        total_statement = total_statement.outerjoin(ClassCourse, ClassCourse.id == Task.class_course_id)
        total_statement = total_statement.outerjoin(Course, Course.id == ClassCourse.course_id)
        total_statement = total_statement.where(self._authorized_feed_condition(user_id))
        total_statement = self._apply_view_filter(total_statement, view)
        total_statement = self._apply_optional_filters(total_statement, visibility, classroom_id, class_course_id, task_type, priority)
        total_statement = self._apply_due_filter(total_statement, due, now_utc, today_start_utc, today_end_utc, week_end_utc)
        total_statement = self._apply_search_filter(total_statement, search)

        statement = self._apply_ordering(statement, view, now_utc, today_start_utc, today_end_utc, week_end_utc)
        statement = statement.offset((page - 1) * page_size).limit(page_size)

        total_result = await self.session.execute(total_statement)
        result = await self.session.execute(statement)

        return FeedQueryResult(
            tasks=[(task, progress) for task, progress in result.all()],
            total=total_result.scalar_one(),
        )

    async def get_summary(
        self,
        user_id: int,
        now_utc: datetime,
        today_start_utc: datetime,
        today_end_utc: datetime,
        week_end_utc: datetime,
        completed_week_start_utc: datetime,
        completed_week_end_utc: datetime,
    ) -> FeedSummaryResult:
        pending_active = self._pending_active_condition()
        completed_condition = self._completed_condition()

        overdue = await self._count_authorized_tasks(
            user_id,
            pending_active,
            Task.deadline < now_utc,
        )
        due_today = await self._count_authorized_tasks(
            user_id,
            pending_active,
            Task.deadline >= today_start_utc,
            Task.deadline < today_end_utc,
        )
        upcoming = await self._count_authorized_tasks(
            user_id,
            pending_active,
            Task.deadline >= today_end_utc,
            Task.deadline < week_end_utc,
        )
        no_deadline = await self._count_authorized_tasks(
            user_id,
            pending_active,
            Task.deadline.is_(None),
        )
        completed_this_week = await self._count_authorized_tasks(
            user_id,
            completed_condition,
            self._completed_at_in_range_condition(completed_week_start_utc, completed_week_end_utc),
        )

        return FeedSummaryResult(
            overdue=overdue,
            due_today=due_today,
            upcoming_seven_days=upcoming,
            no_deadline=no_deadline,
            completed_this_week=completed_this_week,
        )

    async def list_filter_options(self, user_id: int) -> FeedFilterOptionsResult:
        classroom_result = await self.session.execute(
            select(Classroom.id, Classroom.name)
            .join(ClassMembership, ClassMembership.classroom_id == Classroom.id)
            .where(
                ClassMembership.user_id == user_id,
                ClassMembership.status == MEMBERSHIP_STATUS_APPROVED,
                Classroom.is_active.is_(True),
            )
            .order_by(Classroom.name.asc(), Classroom.id.asc())
        )
        course_result = await self.session.execute(
            select(ClassCourse.id, ClassCourse.classroom_id, Course.name, Course.code)
            .join(CourseRegistration, CourseRegistration.class_course_id == ClassCourse.id)
            .join(ClassMembership, ClassMembership.id == CourseRegistration.membership_id)
            .join(Course, Course.id == ClassCourse.course_id)
            .where(
                ClassMembership.user_id == user_id,
                ClassMembership.status == MEMBERSHIP_STATUS_APPROVED,
                CourseRegistration.is_active.is_(True),
                ClassCourse.is_active.is_(True),
            )
            .order_by(Course.name.asc(), ClassCourse.id.asc())
        )

        return FeedFilterOptionsResult(
            classrooms=[
                FeedFilterClassroomRow(id=classroom_id, name=name)
                for classroom_id, name in classroom_result.all()
            ],
            courses=[
                FeedFilterCourseRow(
                    class_course_id=class_course_id,
                    classroom_id=classroom_id,
                    name=name,
                    code=code,
                )
                for class_course_id, classroom_id, name, code in course_result.all()
            ],
        )

    async def user_can_filter_classroom(self, user_id: int, classroom_id: int) -> bool:
        result = await self.session.execute(
            select(ClassMembership.id)
            .where(
                ClassMembership.user_id == user_id,
                ClassMembership.classroom_id == classroom_id,
                ClassMembership.status == MEMBERSHIP_STATUS_APPROVED,
            )
            .limit(1)
        )
        return result.scalar_one_or_none() is not None

    async def user_can_filter_class_course(self, user_id: int, class_course_id: int) -> bool:
        result = await self.session.execute(
            select(CourseRegistration.id)
            .join(ClassMembership, ClassMembership.id == CourseRegistration.membership_id)
            .where(
                ClassMembership.user_id == user_id,
                ClassMembership.status == MEMBERSHIP_STATUS_APPROVED,
                CourseRegistration.class_course_id == class_course_id,
                CourseRegistration.is_active.is_(True),
            )
            .limit(1)
        )
        return result.scalar_one_or_none() is not None

    def _authorized_feed_condition(self, user_id: int):
        approved_classroom_ids = (
            select(ClassMembership.classroom_id)
            .where(
                ClassMembership.user_id == user_id,
                ClassMembership.status == MEMBERSHIP_STATUS_APPROVED,
            )
        )
        registered_course_ids = (
            select(CourseRegistration.class_course_id)
            .join(ClassMembership, ClassMembership.id == CourseRegistration.membership_id)
            .where(
                ClassMembership.user_id == user_id,
                ClassMembership.status == MEMBERSHIP_STATUS_APPROVED,
                CourseRegistration.is_active.is_(True),
            )
        )

        return or_(
            and_(
                Task.visibility == TASK_VISIBILITY_PERSONAL,
                Task.created_by_user_id == user_id,
            ),
            and_(
                Task.visibility == TASK_VISIBILITY_SHARED,
                Task.classroom_id.in_(approved_classroom_ids),
                Task.class_course_id.is_(None),
            ),
            and_(
                Task.visibility == TASK_VISIBILITY_SHARED,
                Task.class_course_id.in_(registered_course_ids),
            ),
        )

    def _progress_join_for_user(self, user_id: int):
        approved_membership_ids = (
            select(ClassMembership.id)
            .where(
                ClassMembership.user_id == user_id,
                ClassMembership.status == MEMBERSHIP_STATUS_APPROVED,
            )
        )
        return and_(
            TaskProgress.task_id == Task.id,
            TaskProgress.membership_id.in_(approved_membership_ids),
        )

    def _apply_view_filter(self, statement: Select, view: FeedView) -> Select:
        if view == "active":
            return statement.where(
                or_(
                    and_(
                        Task.visibility == TASK_VISIBILITY_PERSONAL,
                        Task.status == TASK_STATUS_ACTIVE,
                    ),
                    and_(
                        Task.visibility == TASK_VISIBILITY_SHARED,
                        Task.status == TASK_STATUS_ACTIVE,
                        or_(
                            TaskProgress.id.is_(None),
                            TaskProgress.status != TASK_PROGRESS_COMPLETED,
                        ),
                    ),
                )
            )

        if view == "completed":
            return statement.where(
                or_(
                    and_(
                        Task.visibility == TASK_VISIBILITY_PERSONAL,
                        Task.status == TASK_STATUS_COMPLETED,
                    ),
                    and_(
                        Task.visibility == TASK_VISIBILITY_SHARED,
                        TaskProgress.status == TASK_PROGRESS_COMPLETED,
                    ),
                )
            )

        if view == "archived":
            return statement.where(Task.status == TASK_STATUS_ARCHIVED)

        return statement

    def _apply_optional_filters(
        self,
        statement: Select,
        visibility: FeedVisibility,
        classroom_id: int | None,
        class_course_id: int | None,
        task_type: str | None,
        priority: str | None,
    ) -> Select:
        if visibility != "all":
            statement = statement.where(Task.visibility == visibility)

        if classroom_id is not None:
            statement = statement.where(Task.classroom_id == classroom_id)

        if class_course_id is not None:
            statement = statement.where(Task.class_course_id == class_course_id)

        if task_type is not None:
            statement = statement.where(Task.task_type == task_type)

        if priority is not None:
            statement = statement.where(Task.priority == priority)

        return statement

    def _apply_due_filter(
        self,
        statement: Select,
        due: FeedDueFilter | None,
        now_utc: datetime,
        today_start_utc: datetime,
        today_end_utc: datetime,
        week_end_utc: datetime,
    ) -> Select:
        if due is None:
            return statement

        pending_active = self._pending_active_condition()

        if due == "overdue":
            return statement.where(pending_active, Task.deadline < now_utc)

        if due == "today":
            return statement.where(pending_active, Task.deadline >= today_start_utc, Task.deadline < today_end_utc)

        if due == "week":
            return statement.where(pending_active, Task.deadline >= today_end_utc, Task.deadline < week_end_utc)

        if due == "later":
            return statement.where(pending_active, Task.deadline >= week_end_utc)

        return statement.where(pending_active, Task.deadline.is_(None))

    async def _count_authorized_tasks(self, user_id: int, *conditions) -> int:
        progress_join = self._progress_join_for_user(user_id)
        statement = (
            select(func.count(func.distinct(Task.id)))
            .select_from(Task)
            .outerjoin(TaskProgress, progress_join)
            .where(self._authorized_feed_condition(user_id), *conditions)
        )
        result = await self.session.execute(statement)
        return result.scalar_one()

    def _pending_active_condition(self):
        return or_(
            and_(
                Task.visibility == TASK_VISIBILITY_PERSONAL,
                Task.status == TASK_STATUS_ACTIVE,
            ),
            and_(
                Task.visibility == TASK_VISIBILITY_SHARED,
                Task.status == TASK_STATUS_ACTIVE,
                or_(
                    TaskProgress.id.is_(None),
                    TaskProgress.status != TASK_PROGRESS_COMPLETED,
                ),
            ),
        )

    def _completed_condition(self):
        return or_(
            and_(
                Task.visibility == TASK_VISIBILITY_PERSONAL,
                Task.status == TASK_STATUS_COMPLETED,
            ),
            and_(
                Task.visibility == TASK_VISIBILITY_SHARED,
                TaskProgress.status == TASK_PROGRESS_COMPLETED,
            ),
        )

    def _completed_at_in_range_condition(self, start_utc: datetime, end_utc: datetime):
        return or_(
            and_(
                Task.visibility == TASK_VISIBILITY_PERSONAL,
                Task.completed_at >= start_utc,
                Task.completed_at < end_utc,
            ),
            and_(
                Task.visibility == TASK_VISIBILITY_SHARED,
                TaskProgress.completed_at >= start_utc,
                TaskProgress.completed_at < end_utc,
            ),
        )

    def _apply_ordering(
        self,
        statement: Select,
        view: FeedView,
        now_utc: datetime,
        today_start_utc: datetime,
        today_end_utc: datetime,
        week_end_utc: datetime,
    ) -> Select:
        if view == "completed":
            completed_at = case(
                (Task.visibility == TASK_VISIBILITY_PERSONAL, Task.completed_at),
                else_=TaskProgress.completed_at,
            )
            return statement.order_by(completed_at.desc().nulls_last(), Task.id.desc())

        if view == "archived":
            return statement.order_by(Task.updated_at.desc(), Task.id.desc())

        pending_active = self._pending_active_condition()
        completed = self._completed_condition()
        due_group_weight = case(
            (and_(pending_active, Task.deadline < now_utc), 0),
            (and_(pending_active, Task.deadline >= today_start_utc, Task.deadline < today_end_utc), 1),
            (and_(pending_active, Task.deadline >= today_end_utc, Task.deadline < week_end_utc), 2),
            (and_(pending_active, Task.deadline >= week_end_utc), 3),
            (and_(pending_active, Task.deadline.is_(None)), 4),
            (completed, 5),
            else_=6,
        )
        priority_weight = case(
            (Task.priority == "urgent", 4),
            (Task.priority == "high", 3),
            (Task.priority == "medium", 2),
            (Task.priority == "low", 1),
            else_=0,
        )

        return statement.order_by(
            due_group_weight.asc(),
            Task.deadline.asc().nulls_last(),
            priority_weight.desc(),
            Task.created_at.desc(),
            Task.id.desc(),
        )

    def _apply_search_filter(self, statement: Select, search: str | None) -> Select:
        if search is None:
            return statement

        term = f"%{search}%"
        return statement.where(
            or_(
                Task.title.ilike(term),
                Task.description.ilike(term),
                Classroom.name.ilike(term),
                Course.name.ilike(term),
                Course.code.ilike(term),
            )
        )
