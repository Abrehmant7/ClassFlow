from datetime import datetime

from sqlalchemy import CheckConstraint, DateTime, ForeignKey, Index, Integer, String, UniqueConstraint, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database.base import Base

REMINDER_PENDING = "pending"
REMINDER_SENT = "sent"
REMINDER_CANCELLED = "cancelled"


class Reminder(Base):
    __tablename__ = "reminders"
    __table_args__ = (
        UniqueConstraint(
            "task_id",
            "recipient_user_id",
            "remind_at",
            name="uq_reminders_task_recipient_remind_at",
        ),
        CheckConstraint(
            "status IN ('pending', 'sent', 'cancelled')",
            name="ck_reminders_status",
        ),
        Index("ix_reminders_status_remind_at", "status", "remind_at"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    task_id: Mapped[int] = mapped_column(
        ForeignKey("tasks.id", ondelete="CASCADE"), index=True, nullable=False,
    )
    recipient_user_id: Mapped[int] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), index=True, nullable=False,
    )
    remind_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    status: Mapped[str] = mapped_column(
        String(30), default=REMINDER_PENDING, server_default=REMINDER_PENDING, nullable=False,
    )
    deadline_snapshot: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    sent_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False,
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False,
    )

    task = relationship("Task")
    recipient = relationship("User")
