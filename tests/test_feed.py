from datetime import UTC, datetime, timedelta

import pytest

from app.core.exceptions import ClassFlowError
from app.models.classroom import CLASS_ROLE_REPRESENTATIVE, CLASS_ROLE_STUDENT, MEMBERSHIP_STATUS_APPROVED, ClassMembership, Classroom
from app.models.course import ClassCourse, Course
from app.models.task import (
    TASK_PROGRESS_COMPLETED,
    TASK_STATUS_ACTIVE,
    TASK_STATUS_COMPLETED,
    TASK_VISIBILITY_PERSONAL,
    TASK_VISIBILITY_SHARED,
    Task,
    TaskProgress,
)
from app.models.user import User
from app.repositories.feed import (
    FeedFilterClassroomRow,
    FeedFilterCourseRow,
    FeedFilterOptionsResult,
    FeedQueryResult,
    FeedSummaryResult,
)
from app.services.feed import FeedService


class FakeFeedRepository:
    def __init__(
        self,
        rows: list[tuple[Task, TaskProgress | None]],
        total: int | None = None,
        allowed_classrooms: set[int] | None = None,
        allowed_courses: set[int] | None = None,
        summary_result: FeedSummaryResult | None = None,
        filter_options_result: FeedFilterOptionsResult | None = None,
    ) -> None:
        self.rows = rows
        self.total = len(rows) if total is None else total
        self.allowed_classrooms = allowed_classrooms or set()
        self.allowed_courses = allowed_courses or set()
        self.summary_result = summary_result or FeedSummaryResult(
            overdue=0,
            due_today=0,
            upcoming_seven_days=0,
            no_deadline=0,
            completed_this_week=0,
        )
        self.filter_options_result = filter_options_result or FeedFilterOptionsResult(classrooms=[], courses=[])
        self.last_query: dict | None = None
        self.last_summary_query: dict | None = None
        self.last_filter_options_user_id: int | None = None

    async def list_personal_feed(self, **kwargs) -> FeedQueryResult:
        self.last_query = kwargs
        return FeedQueryResult(tasks=self.rows, total=self.total)

    async def get_summary(self, **kwargs) -> FeedSummaryResult:
        self.last_summary_query = kwargs
        return self.summary_result

    async def list_filter_options(self, user_id: int) -> FeedFilterOptionsResult:
        self.last_filter_options_user_id = user_id
        return self.filter_options_result

    async def user_can_filter_classroom(self, user_id: int, classroom_id: int) -> bool:
        return classroom_id in self.allowed_classrooms

    async def user_can_filter_class_course(self, user_id: int, class_course_id: int) -> bool:
        return class_course_id in self.allowed_courses


class FakeMembershipRepository:
    def __init__(self, memberships: list[ClassMembership]) -> None:
        self.memberships = {
            (membership.user_id, membership.classroom_id): membership
            for membership in memberships
        }

    async def get_by_user_and_class(self, user_id: int, classroom_id: int) -> ClassMembership | None:
        return self.memberships.get((user_id, classroom_id))


def make_user(user_id: int, username: str = "student") -> User:
    return User(id=user_id, username=username, first_name=None, last_name=None)


def make_membership(
    membership_id: int,
    user_id: int,
    classroom_id: int,
    role: str = CLASS_ROLE_STUDENT,
) -> ClassMembership:
    return ClassMembership(
        id=membership_id,
        user_id=user_id,
        classroom_id=classroom_id,
        role=role,
        status=MEMBERSHIP_STATUS_APPROVED,
    )


def make_task(
    task_id: int,
    user_id: int,
    visibility: str,
    status: str = TASK_STATUS_ACTIVE,
    deadline: datetime | None = None,
    classroom: Classroom | None = None,
    class_course: ClassCourse | None = None,
) -> Task:
    now = datetime.now(UTC)
    return Task(
        id=task_id,
        classroom_id=classroom.id if classroom is not None else None,
        class_course_id=class_course.id if class_course is not None else None,
        created_by_user_id=user_id,
        title="Task",
        description=None,
        task_type="assignment",
        visibility=visibility,
        priority="high",
        status=status,
        deadline=deadline,
        completed_at=now if status == TASK_STATUS_COMPLETED else None,
        created_at=now,
        updated_at=now,
        creator=make_user(user_id),
        classroom=classroom,
        class_course=class_course,
        attachments=[],
    )


def make_course_context() -> tuple[Classroom, ClassCourse]:
    classroom = Classroom(id=3, name="BSCS Section A", semester=7, section="A", join_code="ABC12345", creator_id=1)
    course = Course(id=4, name="Database Systems", code="CS301")
    class_course = ClassCourse(
        id=8,
        classroom_id=classroom.id,
        course_id=course.id,
        course=course,
        is_default=False,
        is_active=True,
        created_by_user_id=1,
    )
    return classroom, class_course


@pytest.mark.anyio
async def test_feed_item_normalizes_personal_completion_and_permissions() -> None:
    task = make_task(
        task_id=1,
        user_id=20,
        visibility=TASK_VISIBILITY_PERSONAL,
        status=TASK_STATUS_COMPLETED,
    )
    service = FeedService(
        feed_repository=FakeFeedRepository([(task, None)]),
        membership_repository=FakeMembershipRepository([]),
    )

    response = await service.get_personal_feed(
        user_id=20,
        view="completed",
        visibility="personal",
        classroom_id=None,
        class_course_id=None,
        task_type=None,
        priority=None,
        due=None,
        search=None,
        timezone_name="UTC",
        page=1,
        page_size=20,
    )

    item = response.items[0]
    assert item.my_completion_status == TASK_PROGRESS_COMPLETED
    assert item.due_group == "completed"
    assert item.context_type == "independent"
    assert item.permissions.can_edit is True
    assert item.permissions.can_delete is True
    assert item.permissions.can_update_progress is False


@pytest.mark.anyio
async def test_feed_item_returns_course_context_and_shared_progress_permission() -> None:
    classroom, class_course = make_course_context()
    representative = make_membership(1, user_id=20, classroom_id=classroom.id, role=CLASS_ROLE_REPRESENTATIVE)
    task = make_task(
        task_id=2,
        user_id=10,
        visibility=TASK_VISIBILITY_SHARED,
        classroom=classroom,
        class_course=class_course,
        deadline=datetime.now(UTC) + timedelta(days=1),
    )
    service = FeedService(
        feed_repository=FakeFeedRepository([(task, None)]),
        membership_repository=FakeMembershipRepository([representative]),
    )

    response = await service.get_personal_feed(
        user_id=20,
        view="active",
        visibility="shared",
        classroom_id=None,
        class_course_id=None,
        task_type=None,
        priority=None,
        due=None,
        search=None,
        timezone_name="UTC",
        page=1,
        page_size=20,
    )

    item = response.items[0]
    assert item.context_type == "course"
    assert item.classroom is not None
    assert item.classroom.name == "BSCS Section A"
    assert item.course is not None
    assert item.course.code == "CS301"
    assert item.permissions.can_manage is True
    assert item.permissions.can_update_progress is True


@pytest.mark.anyio
async def test_feed_search_is_trimmed_before_query() -> None:
    repository = FakeFeedRepository([])
    service = FeedService(
        feed_repository=repository,
        membership_repository=FakeMembershipRepository([]),
    )

    await service.get_personal_feed(
        user_id=20,
        view="active",
        visibility="all",
        classroom_id=None,
        class_course_id=None,
        task_type=None,
        priority=None,
        due=None,
        search="  database  ",
        timezone_name="UTC",
        page=1,
        page_size=20,
    )

    assert repository.last_query is not None
    assert repository.last_query["search"] == "database"


@pytest.mark.anyio
async def test_feed_search_too_long_is_rejected_before_query() -> None:
    repository = FakeFeedRepository([])
    service = FeedService(
        feed_repository=repository,
        membership_repository=FakeMembershipRepository([]),
    )

    with pytest.raises(ClassFlowError) as exc_info:
        await service.get_personal_feed(
            user_id=20,
            view="active",
            visibility="all",
            classroom_id=None,
            class_course_id=None,
            task_type=None,
            priority=None,
            due=None,
            search="x" * 101,
            timezone_name="UTC",
            page=1,
            page_size=20,
        )

    assert exc_info.value.detail["error_code"] == "FEED_SEARCH_TOO_LONG"
    assert repository.last_query is None


@pytest.mark.anyio
async def test_feed_rejects_unauthorized_course_filter() -> None:
    service = FeedService(
        feed_repository=FakeFeedRepository([], allowed_courses=set()),
        membership_repository=FakeMembershipRepository([]),
    )

    with pytest.raises(ClassFlowError) as exc_info:
        await service.get_personal_feed(
            user_id=20,
            view="active",
            visibility="all",
            classroom_id=None,
            class_course_id=8,
            task_type=None,
            priority=None,
            due=None,
            search=None,
            timezone_name="UTC",
            page=1,
            page_size=20,
        )

    assert exc_info.value.detail["error_code"] == "FEED_COURSE_FILTER_NOT_AUTHORIZED"


@pytest.mark.anyio
async def test_feed_rejects_invalid_timezone() -> None:
    service = FeedService(
        feed_repository=FakeFeedRepository([]),
        membership_repository=FakeMembershipRepository([]),
    )

    with pytest.raises(ClassFlowError) as exc_info:
        await service.get_personal_feed(
            user_id=20,
            view="active",
            visibility="all",
            classroom_id=None,
            class_course_id=None,
            task_type=None,
            priority=None,
            due=None,
            search=None,
            timezone_name="Not/AZone",
            page=1,
            page_size=20,
        )

    assert exc_info.value.detail["error_code"] == "INVALID_TIMEZONE"


@pytest.mark.anyio
async def test_feed_summary_maps_repository_counts_and_local_boundaries() -> None:
    repository = FakeFeedRepository(
        [],
        summary_result=FeedSummaryResult(
            overdue=2,
            due_today=3,
            upcoming_seven_days=4,
            no_deadline=5,
            completed_this_week=6,
        ),
    )
    service = FeedService(
        feed_repository=repository,
        membership_repository=FakeMembershipRepository([]),
    )

    summary = await service.get_summary(user_id=20, timezone_name="UTC")

    assert summary.overdue == 2
    assert summary.due_today == 3
    assert summary.upcoming_seven_days == 4
    assert summary.no_deadline == 5
    assert summary.completed_this_week == 6
    assert repository.last_summary_query is not None
    assert repository.last_summary_query["user_id"] == 20
    assert repository.last_summary_query["today_start_utc"].tzinfo is UTC
    assert repository.last_summary_query["completed_week_start_utc"].tzinfo is UTC


@pytest.mark.anyio
async def test_feed_filter_options_map_only_allowed_repository_rows() -> None:
    repository = FakeFeedRepository(
        [],
        filter_options_result=FeedFilterOptionsResult(
            classrooms=[FeedFilterClassroomRow(id=3, name="BSCS Section A")],
            courses=[
                FeedFilterCourseRow(
                    class_course_id=8,
                    classroom_id=3,
                    name="Database Systems",
                    code="CS301",
                )
            ],
        ),
    )
    service = FeedService(
        feed_repository=repository,
        membership_repository=FakeMembershipRepository([]),
    )

    options = await service.get_filter_options(user_id=20)

    assert repository.last_filter_options_user_id == 20
    assert len(options.classrooms) == 1
    assert options.classrooms[0].id == 3
    assert options.classrooms[0].name == "BSCS Section A"
    assert len(options.courses) == 1
    assert options.courses[0].class_course_id == 8
    assert options.courses[0].classroom_id == 3
    assert options.courses[0].name == "Database Systems"
    assert options.courses[0].code == "CS301"


def test_feed_due_group_classifies_pending_and_completed_tasks() -> None:
    service = FeedService(
        feed_repository=FakeFeedRepository([]),
        membership_repository=FakeMembershipRepository([]),
    )
    now = datetime(2026, 8, 17, 12, tzinfo=UTC)
    today_start = datetime(2026, 8, 17, tzinfo=UTC)
    today_end = today_start + timedelta(days=1)
    week_end = today_end + timedelta(days=7)

    def build(deadline: datetime | None, status: str = TASK_STATUS_ACTIVE) -> str:
        task = make_task(
            task_id=1,
            user_id=20,
            visibility=TASK_VISIBILITY_PERSONAL,
            status=status,
            deadline=deadline,
        )
        item = service._build_feed_item(
            task=task,
            progress=None,
            membership=None,
            user_id=20,
            now_utc=now,
            today_start_utc=today_start,
            today_end_utc=today_end,
            week_end_utc=week_end,
        )
        return item.due_group

    assert build(now - timedelta(minutes=1)) == "overdue"
    assert build(now + timedelta(hours=2)) == "today"
    assert build(today_end + timedelta(days=2)) == "upcoming"
    assert build(week_end + timedelta(days=1)) == "later"
    assert build(None) == "no_deadline"
    assert build(now - timedelta(days=2), TASK_STATUS_COMPLETED) == "completed"
