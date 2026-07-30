from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

MembershipRole = Literal["representative", "student"]
MembershipStatus = Literal["pending", "approved", "rejected", "removed"]


class ClassroomCreate(BaseModel):
    name: str = Field(min_length=1, max_length=150)
    semester: int = Field(ge=1)
    section: str = Field(min_length=1, max_length=50)
    description: str | None = None


class ClassroomUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=150)
    semester: int | None = Field(default=None, ge=1)
    section: str | None = Field(default=None, min_length=1, max_length=50)
    description: str | None = None
    is_active: bool | None = None


class ClassroomRead(BaseModel):
    id: int
    name: str
    semester: int
    section: str
    description: str | None
    join_code: str
    creator_id: int
    is_active: bool
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class ClassMembershipRead(BaseModel):
    id: int
    user_id: int
    classroom_id: int
    role: MembershipRole
    status: MembershipStatus
    requested_at: datetime
    responded_at: datetime | None
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class ClassroomMineRead(ClassroomRead):
    membership: ClassMembershipRead


class ClassJoinRequest(BaseModel):
    join_code: str = Field(min_length=1, max_length=12)