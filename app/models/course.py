from datetime import datetime

from sqlalchemy import Boolean, DateTime, ForeignKey, Index, Integer, String, Text, UniqueConstraint, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database.base import Base


class Course(Base):
    __tablename__ = "courses"
    __table_args__ = (
        UniqueConstraint("code", name="uq_courses_code"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    name: Mapped[str] = mapped_column(String(150), nullable=False)
    code: Mapped[str] = mapped_column(String(50), nullable=False)
    description: Mapped[str | None] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)

    class_courses: Mapped[list[ClassCourse]] = relationship(
        "ClassCourse",
        back_populates="course",
        cascade="all, delete-orphan",
    )


Index("uq_courses_lower_name", func.lower(Course.name), unique=True)


class ClassCourse(Base):
    __tablename__ = "class_courses"
    __table_args__ = (
        UniqueConstraint("classroom_id", "course_id", name="uq_class_courses_classroom_course"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    classroom_id: Mapped[int] = mapped_column(ForeignKey("classrooms.id", ondelete="CASCADE"), index=True, nullable=False)
    course_id: Mapped[int] = mapped_column(ForeignKey("courses.id", ondelete="CASCADE"), index=True, nullable=False)
    instructor_name: Mapped[str | None] = mapped_column(String(150))
    is_default: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    created_by_user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)

    classroom = relationship("Classroom")
    course: Mapped[Course] = relationship("Course", back_populates="class_courses")
    created_by_user = relationship("User")
    registrations: Mapped[list[CourseRegistration]] = relationship(
        "CourseRegistration",
        back_populates="class_course",
        cascade="all, delete-orphan",
    )
    tasks: Mapped[list["Task"]] = relationship(
        "Task",
        back_populates="class_course",
    )


class CourseRegistration(Base):
    __tablename__ = "course_registrations"
    __table_args__ = (
        UniqueConstraint("membership_id", "class_course_id", name="uq_course_registrations_membership_class_course"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    membership_id: Mapped[int] = mapped_column(ForeignKey("class_memberships.id", ondelete="CASCADE"), index=True, nullable=False)
    class_course_id: Mapped[int] = mapped_column(ForeignKey("class_courses.id", ondelete="CASCADE"), index=True, nullable=False)
    registered_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    dropped_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)

    membership = relationship("ClassMembership")
    class_course: Mapped[ClassCourse] = relationship("ClassCourse", back_populates="registrations")