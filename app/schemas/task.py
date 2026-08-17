from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator

TaskType = Literal["assignment", "quiz", "lab", "project", "presentation", "exam", "other"]
TaskVisibility = Literal["shared", "personal"]
TaskPriority = Literal["low", "medium", "high", "urgent"]
TaskStatus = Literal["active", "completed", "cancelled", "archived"]
TaskProgressStatus = Literal["pending", "completed"]


class TaskCreatorRead(BaseModel):
    id: int
    username: str
    first_name: str | None
    last_name: str | None
    roll_number: str | None

    model_config = ConfigDict(from_attributes=True)


class TaskCourseRead(BaseModel):
    id: int
    name: str
    code: str

    model_config = ConfigDict(from_attributes=True)


class TaskCreate(BaseModel):
    title: str = Field(min_length=1, max_length=200)
    description: str | None = None
    classroom_id: int | None = Field(default=None, ge=1)
    class_course_id: int | None = Field(default=None, ge=1)
    task_type: TaskType = "other"
    visibility: TaskVisibility
    priority: TaskPriority = "medium"
    deadline: datetime | None = None

    @field_validator("deadline")
    @classmethod
    def validate_deadline_timezone(cls, value: datetime | None) -> datetime | None:
        if value is not None and value.tzinfo is None:
            raise ValueError("Deadline must be timezone-aware")
        return value


class PersonalTaskCreate(BaseModel):
    title: str = Field(min_length=1, max_length=200)
    description: str | None = None
    classroom_id: int | None = Field(default=None, ge=1)
    class_course_id: int | None = Field(default=None, ge=1)
    task_type: TaskType = "other"
    priority: TaskPriority = "medium"
    deadline: datetime | None = None

    @field_validator("deadline")
    @classmethod
    def validate_deadline_timezone(cls, value: datetime | None) -> datetime | None:
        if value is not None and value.tzinfo is None:
            raise ValueError("Deadline must be timezone-aware")
        return value

    def to_task_create(self) -> TaskCreate:
        return TaskCreate(
            title=self.title,
            description=self.description,
            classroom_id=self.classroom_id,
            class_course_id=self.class_course_id,
            task_type=self.task_type,
            visibility="personal",
            priority=self.priority,
            deadline=self.deadline,
        )


class TaskUpdate(BaseModel):
    title: str | None = Field(default=None, min_length=1, max_length=200)
    description: str | None = None
    task_type: TaskType | None = None
    priority: TaskPriority | None = None
    status: TaskStatus | None = None
    deadline: datetime | None = None

    @field_validator("deadline")
    @classmethod
    def validate_deadline_timezone(cls, value: datetime | None) -> datetime | None:
        if value is not None and value.tzinfo is None:
            raise ValueError("Deadline must be timezone-aware")
        return value


class TaskProgressUpdate(BaseModel):
    status: TaskProgressStatus


class TaskProgressRead(BaseModel):
    status: TaskProgressStatus
    completed_at: datetime | None = None


class TaskAttachmentRead(BaseModel):
    id: int
    task_id: int
    uploaded_by_user_id: int
    file_name: str
    file_type: str
    file_size: int
    uploaded_at: datetime

    model_config = ConfigDict(from_attributes=True)


class TaskAttachmentDownload(BaseModel):
    file_path: str
    file_name: str
    file_type: str


class TaskListItem(BaseModel):
    id: int
    classroom_id: int | None
    class_course_id: int | None
    created_by_user_id: int
    title: str
    description: str | None
    task_type: TaskType
    visibility: TaskVisibility
    priority: TaskPriority
    status: TaskStatus
    deadline: datetime | None
    completed_at: datetime | None
    created_at: datetime
    updated_at: datetime
    creator: TaskCreatorRead
    course: TaskCourseRead | None = None
    my_progress: TaskProgressRead
    can_manage: bool

    model_config = ConfigDict(from_attributes=True)


class TaskRead(TaskListItem):
    attachments: list[TaskAttachmentRead] = []
