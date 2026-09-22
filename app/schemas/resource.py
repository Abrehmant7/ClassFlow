from datetime import datetime
from typing import Annotated, Literal

from pydantic import BaseModel, ConfigDict, Field, StringConstraints, field_validator

ResourceIndexingStatus = Literal["pending", "processing", "indexed", "failed"]
ResourceTitle = Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=200)]


class ResourceCreate(BaseModel):
    title: ResourceTitle
    description: str | None = None
    class_course_id: int | None = Field(default=None, ge=1)

    model_config = ConfigDict(str_strip_whitespace=True, extra="forbid")


class ResourceUpdate(BaseModel):
    title: str | None = Field(default=None, min_length=1, max_length=200)
    description: str | None = None
    is_enabled: bool | None = None

    model_config = ConfigDict(str_strip_whitespace=True, extra="forbid")

    @field_validator("title", "is_enabled")
    @classmethod
    def reject_explicit_null(cls, value):
        if value is None:
            raise ValueError("This field cannot be null")
        return value


class ResourceRead(BaseModel):
    id: int
    classroom_id: int
    class_course_id: int | None
    uploaded_by_user_id: int
    title: str
    description: str | None
    file_name: str
    content_type: str
    file_size: int | None
    is_enabled: bool
    indexing_status: ResourceIndexingStatus
    indexing_error: str | None
    indexed_at: datetime | None
    created_at: datetime
    updated_at: datetime
    can_manage: bool

    model_config = ConfigDict(from_attributes=True)


class ResourceDownload(BaseModel):
    """Internal download descriptor; never use as an API response model."""

    file_path: str = Field(exclude=True, repr=False)
    file_name: str
    content_type: str
