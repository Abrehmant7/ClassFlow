from datetime import datetime

from sqlalchemy import and_, or_, select
from sqlalchemy.orm import selectinload

from app.models.classroom import CLASS_ROLE_REPRESENTATIVE, MEMBERSHIP_STATUS_APPROVED, ClassMembership
from app.models.course import ClassCourse, CourseRegistration
from app.models.task import (
    TASK_STATUS_ACTIVE,
    TASK_VISIBILITY_PERSONAL,
    TASK_VISIBILITY_SHARED,
    Task,
    TaskAttachment,
    TaskProgress,
)
from app.repositories.base import BaseRepository
from app.schemas.task import TaskCreate, TaskUpdate


class TaskRepository(BaseRepository[Task]):
    async def create(self, classroom_id: int | None, task_in: TaskCreate, created_by_user_id: int) -> Task:
        task = Task(
            classroom_id=classroom_id,
            class_course_id=task_in.class_course_id,
            created_by_user_id=created_by_user_id,
            title=task_in.title,
            description=task_in.description,
            task_type=task_in.task_type,
            visibility=task_in.visibility,
            priority=task_in.priority,
            status=TASK_STATUS_ACTIVE,
            deadline=task_in.deadline,
        )
        self.session.add(task)
        await self.session.flush()
        return task

    async def get_by_id(self, task_id: int) -> Task | None:
        result = await self.session.execute(
            select(Task)
            .options(
                selectinload(Task.creator),
                selectinload(Task.attachments),
                selectinload(Task.class_course).selectinload(ClassCourse.course),
            )
            .where(Task.id == task_id)
        )
        return result.scalar_one_or_none()

    async def list_accessible_for_class(
        self,
        classroom_id: int,
        user_id: int,
        membership_id: int,
        is_representative: bool,
        include_closed: bool = False,
    ) -> list[Task]:
        statement = (
            select(Task)
            .options(
                selectinload(Task.creator),
                selectinload(Task.attachments),
                selectinload(Task.class_course).selectinload(ClassCourse.course),
            )
            .where(Task.classroom_id == classroom_id)
        )

        if not include_closed:
            statement = statement.where(Task.status == TASK_STATUS_ACTIVE)

        if is_representative:
            # Representatives can manage shared tasks, but personal tasks still remain creator-only.
            statement = statement.where(
                or_(
                    Task.visibility == TASK_VISIBILITY_SHARED,
                    and_(
                        Task.visibility == TASK_VISIBILITY_PERSONAL,
                        Task.created_by_user_id == user_id,
                    ),
                )
            )
        else:
            # Course-linked shared tasks are visible only to actively registered members.
            registered_course_ids = (
                select(CourseRegistration.class_course_id)
                .where(
                    CourseRegistration.membership_id == membership_id,
                    CourseRegistration.is_active.is_(True),
                )
            )

            statement = statement.where(
                or_(
                    and_(
                        Task.visibility == TASK_VISIBILITY_PERSONAL,
                        Task.created_by_user_id == user_id,
                    ),
                    and_(
                        Task.visibility == TASK_VISIBILITY_SHARED,
                        Task.class_course_id.is_(None),
                    ),
                    and_(
                        Task.visibility == TASK_VISIBILITY_SHARED,
                        Task.class_course_id.in_(registered_course_ids),
                    ),
                )
            )

        statement = statement.order_by(Task.deadline.asc().nulls_last(), Task.created_at.desc())

        result = await self.session.execute(statement)
        return list(result.scalars().all())

    async def list_feed_for_user(self, user_id: int, include_closed: bool = False) -> list[Task]:
        approved_membership_ids = (
            select(ClassMembership.id)
            .where(
                ClassMembership.user_id == user_id,
                ClassMembership.status == MEMBERSHIP_STATUS_APPROVED,
            )
        )
        approved_classroom_ids = (
            select(ClassMembership.classroom_id)
            .where(
                ClassMembership.user_id == user_id,
                ClassMembership.status == MEMBERSHIP_STATUS_APPROVED,
            )
        )
        representative_classroom_ids = (
            select(ClassMembership.classroom_id)
            .where(
                ClassMembership.user_id == user_id,
                ClassMembership.status == MEMBERSHIP_STATUS_APPROVED,
                ClassMembership.role == CLASS_ROLE_REPRESENTATIVE,
            )
        )
        registered_course_ids = (
            select(CourseRegistration.class_course_id)
            .where(
                CourseRegistration.membership_id.in_(approved_membership_ids),
                CourseRegistration.is_active.is_(True),
            )
        )

        # Feed visibility combines creator-owned personal tasks with shared tasks from approved classes.
        statement = (
            select(Task)
            .options(
                selectinload(Task.creator),
                selectinload(Task.attachments),
                selectinload(Task.class_course).selectinload(ClassCourse.course),
            )
            .where(
                or_(
                    and_(
                        Task.visibility == TASK_VISIBILITY_PERSONAL,
                        Task.created_by_user_id == user_id,
                    ),
                    and_(
                        Task.visibility == TASK_VISIBILITY_SHARED,
                        Task.classroom_id.in_(approved_classroom_ids),
                        or_(
                            Task.class_course_id.is_(None),
                            Task.class_course_id.in_(registered_course_ids),
                            Task.classroom_id.in_(representative_classroom_ids),
                        ),
                    ),
                )
            )
        )

        if not include_closed:
            statement = statement.where(Task.status == TASK_STATUS_ACTIVE)

        statement = statement.order_by(Task.deadline.asc().nulls_last(), Task.created_at.desc())

        result = await self.session.execute(statement)
        return list(result.scalars().all())

    async def update(self, task: Task, task_in: TaskUpdate) -> Task:
        update_data = task_in.model_dump(exclude_unset=True)

        for field, value in update_data.items():
            setattr(task, field, value)

        await self.session.flush()
        return task

    async def delete(self, task: Task) -> None:
        await self.session.delete(task)
        await self.session.flush()


class TaskProgressRepository(BaseRepository[TaskProgress]):
    async def get_by_task_and_membership(self, task_id: int, membership_id: int) -> TaskProgress | None:
        result = await self.session.execute(
            select(TaskProgress).where(
                TaskProgress.task_id == task_id,
                TaskProgress.membership_id == membership_id,
            )
        )
        return result.scalar_one_or_none()

    async def upsert_for_membership(
        self,
        task_id: int,
        membership_id: int,
        progress_status: str,
        completed_at: datetime | None,
    ) -> TaskProgress:
        # No row means pending, so create a row only once the student actively changes progress.
        progress = await self.get_by_task_and_membership(task_id, membership_id)

        if progress is None:
            progress = TaskProgress(
                task_id=task_id,
                membership_id=membership_id,
                status=progress_status,
                completed_at=completed_at,
            )
            self.session.add(progress)
        else:
            progress.status = progress_status
            progress.completed_at = completed_at

        await self.session.flush()
        return progress


class TaskAttachmentRepository(BaseRepository[TaskAttachment]):
    async def create(
        self,
        task_id: int,
        uploaded_by_user_id: int,
        file_name: str,
        storage_key: str,
        file_type: str,
        file_size: int,
    ) -> TaskAttachment:
        attachment = TaskAttachment(
            task_id=task_id,
            uploaded_by_user_id=uploaded_by_user_id,
            file_name=file_name,
            storage_key=storage_key,
            file_type=file_type,
            file_size=file_size,
        )
        self.session.add(attachment)
        await self.session.flush()
        return attachment

    async def get_by_id(self, attachment_id: int) -> TaskAttachment | None:
        result = await self.session.execute(
            select(TaskAttachment)
            .options(
                selectinload(TaskAttachment.task)
                .selectinload(Task.class_course)
                .selectinload(ClassCourse.course),
                selectinload(TaskAttachment.task).selectinload(Task.creator),
                selectinload(TaskAttachment.task).selectinload(Task.attachments),
            )
            .where(TaskAttachment.id == attachment_id)
        )
        return result.scalar_one_or_none()

    async def list_for_task(self, task_id: int) -> list[TaskAttachment]:
        result = await self.session.execute(
            select(TaskAttachment)
            .where(TaskAttachment.task_id == task_id)
            .order_by(TaskAttachment.uploaded_at.desc())
        )
        return list(result.scalars().all())

    async def delete(self, attachment: TaskAttachment) -> None:
        await self.session.delete(attachment)
        await self.session.flush()
