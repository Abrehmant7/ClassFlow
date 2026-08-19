from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict

from app.schemas.task import TaskPriority, TaskProgressStatus, TaskStatus, TaskType, TaskVisibility

FeedView = Literal["active", "completed", "archived", "all"]
FeedVisibility = Literal["all", "personal", "shared"]
FeedDueFilter = Literal["overdue", "today", "week", "later", "no_deadline"]
FeedDueGroup = Literal["overdue", "today", "upcoming", "later", "no_deadline", "completed"]
FeedContextType = Literal["independent", "class", "course"]


class FeedTaskClassroom(BaseModel):
    id: int
    name: str

    model_config = ConfigDict(from_attributes=True)


class FeedTaskCourse(BaseModel):
    class_course_id: int
    course_id: int
    name: str
    code: str


class FeedTaskCreator(BaseModel):
    id: int
    name: str


class FeedTaskPermissions(BaseModel):
    can_edit: bool
    can_delete: bool
    can_manage: bool
    can_update_progress: bool


class FeedTaskItem(BaseModel):
    id: int
    title: str
    description: str | None
    visibility: TaskVisibility
    task_type: TaskType
    priority: TaskPriority
    task_status: TaskStatus
    my_completion_status: TaskProgressStatus
    my_completed_at: datetime | None
    deadline: datetime | None
    is_overdue: bool
    due_group: FeedDueGroup
    context_type: FeedContextType
    classroom: FeedTaskClassroom | None
    course: FeedTaskCourse | None
    creator: FeedTaskCreator
    attachment_count: int
    permissions: FeedTaskPermissions
    created_at: datetime
    updated_at: datetime


class FeedResponse(BaseModel):
    items: list[FeedTaskItem]
    page: int
    page_size: int
    total: int
    total_pages: int


class FeedSummary(BaseModel):
    overdue: int
    due_today: int
    upcoming_seven_days: int
    no_deadline: int
    completed_this_week: int


class FeedFilterClassroom(BaseModel):
    id: int
    name: str


class FeedFilterCourse(BaseModel):
    class_course_id: int
    classroom_id: int
    name: str
    code: str


class FeedFilterOptions(BaseModel):
    classrooms: list[FeedFilterClassroom]
    courses: list[FeedFilterCourse]
