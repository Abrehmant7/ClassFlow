"""SQLAlchemy models will be exported here for Alembic autogeneration."""

from app.models.classroom import Classroom, ClassMembership
from app.models.course import Course, ClassCourse, CourseRegistration
from app.models.refresh_token import RefreshToken
from app.models.task import Task, TaskAttachment, TaskProgress
from app.models.user import User

__all__ = [
    "ClassMembership",
    "Classroom",
    "ClassCourse",
    "Course",
    "CourseRegistration",
    "RefreshToken",
    "Task",
    "TaskAttachment",
    "TaskProgress",
    "User",
]