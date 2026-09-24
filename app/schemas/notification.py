from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field


NotificationEventType = Literal[
    "membership_request",
    "membership_approved",
    "membership_rejected",
    "task_created",
    "task_updated",
    "announcement_posted",
    "deadline_approaching",
]


class NotificationRead(BaseModel):
    id: int
    event_type: str
    title: str
    message: str
    classroom_id: int | None
    source_type: str
    source_id: int
    action_url: str
    is_read: bool
    read_at: datetime | None
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class NotificationListResponse(BaseModel):
    items: list[NotificationRead]
    total: int = Field(ge=0)
    page: int = Field(ge=1)
    page_size: int = Field(ge=1)


class UnreadNotificationCount(BaseModel):
    unread_count: int = Field(ge=0)


class NotificationMarkAllResponse(BaseModel):
    updated_count: int = Field(ge=0)
