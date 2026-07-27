from datetime import datetime

from sqlalchemy import Boolean, CheckConstraint, DateTime, ForeignKey, Integer, String, Text, UniqueConstraint, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database.base import Base

CLASS_ROLE_REPRESENTATIVE = "representative"
CLASS_ROLE_STUDENT = "student"

MEMBERSHIP_STATUS_PENDING = "pending"
MEMBERSHIP_STATUS_APPROVED = "approved"
MEMBERSHIP_STATUS_REJECTED = "rejected"
MEMBERSHIP_STATUS_REMOVED = "removed"


class Classroom(Base):
    __tablename__ = "classrooms"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    name: Mapped[str] = mapped_column(String(150), nullable=False)
    semester: Mapped[int] = mapped_column(Integer, nullable=False)
    section: Mapped[str] = mapped_column(String(50), nullable=False)
    description: Mapped[str | None] = mapped_column(Text)
    join_code: Mapped[str] = mapped_column(String(12), unique=True, index=True, nullable=False)
    creator_id: Mapped[int] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"),
        index=True,
        nullable=False,
    )
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)

    creator = relationship("User")
    memberships: Mapped[list["ClassMembership"]] = relationship(
        "ClassMembership",
        back_populates="classroom",
        cascade="all, delete-orphan",
    )


class ClassMembership(Base):
    __tablename__ = "class_memberships"
    __table_args__ = (
        UniqueConstraint("user_id", "classroom_id", name="uq_class_memberships_user_classroom"),
        CheckConstraint(
            "role IN ('representative', 'student')",
            name="ck_class_memberships_role",
        ),
        CheckConstraint(
            "status IN ('pending', 'approved', 'rejected', 'removed')",
            name="ck_class_memberships_status",
        ),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True, nullable=False)
    classroom_id: Mapped[int] = mapped_column(ForeignKey("classrooms.id", ondelete="CASCADE"), index=True, nullable=False)
    role: Mapped[str] = mapped_column(String(30), default=CLASS_ROLE_STUDENT, nullable=False)
    status: Mapped[str] = mapped_column(String(30), default=MEMBERSHIP_STATUS_PENDING, nullable=False)
    requested_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    responded_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)

    user = relationship("User")
    classroom: Mapped[Classroom] = relationship("Classroom", back_populates="memberships")