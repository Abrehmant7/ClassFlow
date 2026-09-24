from datetime import datetime
from typing import Literal

from pydantic import BaseModel, Field

from app.schemas.task import TaskPriority, TaskStatus, TaskType


SearchEntityType = Literal["all", "task", "announcement", "resource"]
SearchResultEntityType = Literal["task", "announcement", "resource"]


class SearchResultItem(BaseModel):
    entity_type: SearchResultEntityType
    id: int
    title: str
    preview: str
    classroom_id: int | None
    class_course_id: int | None
    date: datetime | None
    task_type: TaskType | None = None
    priority: TaskPriority | None = None
    status: TaskStatus | None = None
    action_url: str


class SearchResponse(BaseModel):
    items: list[SearchResultItem]
    total: int = Field(ge=0)
    page: int = Field(ge=1)
    page_size: int = Field(ge=1)
    total_pages: int = Field(ge=0)
