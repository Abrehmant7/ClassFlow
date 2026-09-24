from datetime import datetime

from sqlalchemy import Boolean, CheckConstraint, DateTime, ForeignKey, Index, Integer, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database.base import Base

NOTIFICATION_MEMBERSHIP_REQUEST = "membership_request"
NOTIFICATION_MEMBERSHIP_APPROVED = "membership_approved"
NOTIFICATION_MEMBERSHIP_REJECTED = "membership_rejected"
NOTIFICATION_TASK_CREATED = "task_created"
NOTIFICATION_TASK_UPDATED = "task_updated"
NOTIFICATION_ANNOUNCEMENT_POSTED = "announcement_posted"
NOTIFICATION_DEADLINE_APPROACHING = "deadline_approaching"

NOTIFICATION_EVENT_TYPES = (
    NOTIFICATION_MEMBERSHIP_REQUEST,
    NOTIFICATION_MEMBERSHIP_APPROVED,
    NOTIFICATION_MEMBERSHIP_REJECTED,
    NOTIFICATION_TASK_CREATED,
    NOTIFICATION_TASK_UPDATED,
    NOTIFICATION_ANNOUNCEMENT_POSTED,
    NOTIFICATION_DEADLINE_APPROACHING,
)


class Notification(Base):
    __tablename__ = "notifications"
    __table_args__ = (
        CheckConstraint(
            "event_type IN ('membership_request', 'membership_approved', "
            "'membership_rejected', 'task_created', 'task_updated', "
            "'announcement_posted', 'deadline_approaching')",
            name="ck_notifications_event_type",
        ),
        Index(
            "ix_notifications_recipient_read_created",
            "recipient_user_id",
            "is_read",
            "created_at",
        ),
        Index("ix_notifications_dedupe_key", "dedupe_key", unique=True),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    recipient_user_id: Mapped[int] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), index=True, nullable=False,
    )
    actor_user_id: Mapped[int | None] = mapped_column(
        ForeignKey("users.id", ondelete="SET NULL"), index=True,
    )
    classroom_id: Mapped[int | None] = mapped_column(
        ForeignKey("classrooms.id", ondelete="CASCADE"), index=True,
    )
    event_type: Mapped[str] = mapped_column(String(40), nullable=False)
    title: Mapped[str] = mapped_column(String(200), nullable=False)
    message: Mapped[str] = mapped_column(Text, nullable=False)
    source_type: Mapped[str] = mapped_column(String(40), nullable=False)
    source_id: Mapped[int] = mapped_column(Integer, nullable=False)
    action_url: Mapped[str] = mapped_column(String(500), nullable=False)
    dedupe_key: Mapped[str | None] = mapped_column(String(500))
    is_read: Mapped[bool] = mapped_column(Boolean, default=False, server_default="false", nullable=False)
    read_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False,
    )

    recipient = relationship("User", foreign_keys=[recipient_user_id])
    actor = relationship("User", foreign_keys=[actor_user_id])
    classroom = relationship("Classroom")
