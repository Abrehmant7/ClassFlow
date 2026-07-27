from pydantic import BaseModel, ConfigDict, EmailStr


class UserCreate(BaseModel):
    username: str
    email: EmailStr
    password: str
    first_name: str | None = None
    last_name: str | None = None
    roll_number: str | None = None
    semester: int | None = None
    section: str | None = None


class UserUpdate(BaseModel):
    first_name: str | None = None
    last_name: str | None = None
    roll_number: str | None = None
    semester: int | None = None
    section: str | None = None


class UserRead(BaseModel):
    id: int
    username: str
    email: EmailStr
    first_name: str | None
    last_name: str | None
    roll_number: str | None
    semester: int | None
    section: str | None
    is_active: bool
    is_superuser: bool

    model_config = ConfigDict(from_attributes=True)