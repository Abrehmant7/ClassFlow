from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field


class CourseCreate(BaseModel):
    name: str = Field(min_length=1, max_length=150)
    code: str = Field(min_length=1, max_length=50)
    description: str | None = None


class CourseRead(BaseModel):
    id: int
    name: str
    code: str
    description: str | None
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class ClassCourseCreate(BaseModel):
    course_id: int = Field(ge=1)
    instructor_name: str | None = Field(default=None, max_length=150)
    is_default: bool = False


class ClassCourseUpdate(BaseModel):
    instructor_name: str | None = Field(default=None, max_length=150)
    is_default: bool | None = None
    is_active: bool | None = None


class ClassCourseRead(BaseModel):
    id: int
    classroom_id: int
    course_id: int
    instructor_name: str | None
    is_default: bool
    is_active: bool
    created_by_user_id: int
    course: CourseRead
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class CourseRegistrationRead(BaseModel):
    id: int
    membership_id: int
    class_course_id: int
    registered_at: datetime
    dropped_at: datetime | None
    is_active: bool
    class_course: ClassCourseRead

    model_config = ConfigDict(from_attributes=True)