from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field, field_validator


class AnnouncementCreate(BaseModel):
    title: str = Field(min_length=1, max_length=200)
    body: str = Field(min_length=1)
    class_course_id: int | None = Field(default=None, ge=1)
    is_pinned: bool = False

    model_config = ConfigDict(str_strip_whitespace=True, extra="forbid")


class AnnouncementUpdate(BaseModel):
    title: str | None = Field(default=None, min_length=1, max_length=200)
    body: str | None = Field(default=None, min_length=1)
    class_course_id: int | None = Field(default=None, ge=1)
    is_pinned: bool | None = None

    model_config = ConfigDict(str_strip_whitespace=True, extra="forbid")

    @field_validator("title", "body", "is_pinned")
    @classmethod
    def reject_explicit_null(cls, value):
        if value is None:
            raise ValueError("This field cannot be null")
        return value


class AnnouncementRead(BaseModel):
    id: int
    classroom_id: int
    class_course_id: int | None
    created_by_user_id: int
    title: str
    body: str
    is_pinned: bool
    created_at: datetime
    updated_at: datetime
    can_manage: bool

    model_config = ConfigDict(from_attributes=True)
