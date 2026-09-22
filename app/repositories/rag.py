from typing import NamedTuple

from sqlalchemy import Select, and_, delete, exists, or_, select
from sqlalchemy.orm import selectinload

from app.models.announcement import Announcement
from app.models.classroom import CLASS_ROLE_REPRESENTATIVE, MEMBERSHIP_STATUS_APPROVED, ClassMembership, Classroom
from app.models.course import ClassCourse, CourseRegistration
from app.models.resource import (
    RAG_SOURCE_ANNOUNCEMENT,
    RAG_SOURCE_COURSE,
    RAG_SOURCE_RESOURCE,
    RAG_SOURCE_TASK,
    RAG_SOURCE_TASK_ATTACHMENT,
    RESOURCE_INDEX_INDEXED,
    RagChunk,
    Resource,
)
from app.models.task import TASK_STATUS_ACTIVE, TASK_VISIBILITY_SHARED, Task, TaskAttachment
from app.repositories.base import BaseRepository


class RagSearchResult(NamedTuple):
    chunk: RagChunk
    distance: float


class RagAttachmentSource(NamedTuple):
    attachment: TaskAttachment
    task: Task


class RagRepository(BaseRepository[RagChunk]):
    async def user_has_approved_class_access(
        self,
        classroom_id: int,
        user_id: int,
    ) -> bool:
        result = await self.session.execute(
            select(
                exists().where(
                    ClassMembership.user_id == user_id,
                    ClassMembership.classroom_id == classroom_id,
                    ClassMembership.status == MEMBERSHIP_STATUS_APPROVED,
                    Classroom.id == ClassMembership.classroom_id,
                    Classroom.is_active.is_(True),
                )
            )
        )
        return bool(result.scalar_one())

    async def list_indexable_tasks(self, classroom_id: int) -> list[Task]:
        result = await self.session.execute(
            select(Task)
            .where(
                Task.classroom_id == classroom_id,
                Task.visibility == TASK_VISIBILITY_SHARED,
                Task.status == TASK_STATUS_ACTIVE,
                or_(
                    Task.class_course_id.is_(None),
                    Task.class_course.has(ClassCourse.is_active.is_(True)),
                ),
            )
            .order_by(Task.id.asc())
        )
        return list(result.scalars().all())

    async def list_indexable_class_courses(self, classroom_id: int) -> list[ClassCourse]:
        result = await self.session.execute(
            select(ClassCourse)
            .options(selectinload(ClassCourse.course))
            .where(
                ClassCourse.classroom_id == classroom_id,
                ClassCourse.is_active.is_(True),
            )
            .order_by(ClassCourse.id.asc())
        )
        return list(result.scalars().all())

    async def list_indexable_task_attachments(self, classroom_id: int) -> list[RagAttachmentSource]:
        result = await self.session.execute(
            select(TaskAttachment, Task)
            .join(Task, Task.id == TaskAttachment.task_id)
            .where(
                Task.classroom_id == classroom_id,
                Task.visibility == TASK_VISIBILITY_SHARED,
                Task.status == TASK_STATUS_ACTIVE,
                or_(
                    Task.class_course_id.is_(None),
                    Task.class_course.has(ClassCourse.is_active.is_(True)),
                ),
            )
            .order_by(TaskAttachment.id.asc())
        )
        return [
            RagAttachmentSource(attachment=attachment, task=task)
            for attachment, task in result.all()
        ]

    async def search_accessible(
        self,
        classroom_id: int,
        user_id: int,
        query_embedding: list[float],
        limit: int,
        max_distance: float,
    ) -> list[RagSearchResult]:
        result = await self.session.execute(
            self._accessible_search_statement(
                classroom_id=classroom_id,
                user_id=user_id,
                query_embedding=query_embedding,
                limit=limit,
                max_distance=max_distance,
            )
        )
        return [
            RagSearchResult(chunk=chunk, distance=float(distance))
            for chunk, distance in result.all()
        ]

    def _accessible_search_statement(
        self,
        classroom_id: int,
        user_id: int,
        query_embedding: list[float],
        limit: int,
        max_distance: float,
    ) -> Select:
        approved_membership_ids = (
            select(ClassMembership.id)
            .join(Classroom, Classroom.id == ClassMembership.classroom_id)
            .where(
                ClassMembership.user_id == user_id,
                ClassMembership.classroom_id == classroom_id,
                ClassMembership.status == MEMBERSHIP_STATUS_APPROVED,
                Classroom.is_active.is_(True),
            )
        )
        registered_class_course_ids = (
            select(CourseRegistration.class_course_id)
            .join(ClassCourse, ClassCourse.id == CourseRegistration.class_course_id)
            .where(
                CourseRegistration.membership_id.in_(approved_membership_ids),
                CourseRegistration.is_active.is_(True),
                ClassCourse.classroom_id == classroom_id,
                ClassCourse.is_active.is_(True),
            )
        )
        representative_access = exists(
            approved_membership_ids.where(ClassMembership.role == CLASS_ROLE_REPRESENTATIVE)
        )
        active_class_course_ids = select(ClassCourse.id).where(
            ClassCourse.classroom_id == classroom_id,
            ClassCourse.is_active.is_(True),
        )
        valid_announcement_source = exists(
            select(Announcement.id).where(
                Announcement.id == RagChunk.source_id,
                Announcement.classroom_id == RagChunk.classroom_id,
                Announcement.class_course_id.is_not_distinct_from(RagChunk.class_course_id),
            )
        )
        valid_task_source = exists(
            select(Task.id).where(
                Task.id == RagChunk.source_id,
                Task.classroom_id == RagChunk.classroom_id,
                Task.class_course_id.is_not_distinct_from(RagChunk.class_course_id),
                Task.visibility == TASK_VISIBILITY_SHARED,
                Task.status == TASK_STATUS_ACTIVE,
            )
        )
        valid_resource_source = exists(
            select(Resource.id).where(
                Resource.id == RagChunk.source_id,
                Resource.classroom_id == RagChunk.classroom_id,
                Resource.class_course_id.is_not_distinct_from(RagChunk.class_course_id),
                Resource.is_enabled.is_(True),
                Resource.indexing_status == RESOURCE_INDEX_INDEXED,
            )
        )
        valid_task_attachment_source = exists(
            select(TaskAttachment.id)
            .join(Task, Task.id == TaskAttachment.task_id)
            .where(
                TaskAttachment.id == RagChunk.source_id,
                Task.classroom_id == RagChunk.classroom_id,
                Task.class_course_id.is_not_distinct_from(RagChunk.class_course_id),
                Task.visibility == TASK_VISIBILITY_SHARED,
                Task.status == TASK_STATUS_ACTIVE,
            )
        )
        valid_course_source = exists(
            select(ClassCourse.id).where(
                ClassCourse.id == RagChunk.source_id,
                ClassCourse.classroom_id == RagChunk.classroom_id,
                RagChunk.class_course_id == ClassCourse.id,
                ClassCourse.is_active.is_(True),
            )
        )
        valid_source = or_(
            and_(RagChunk.source_type == RAG_SOURCE_ANNOUNCEMENT, valid_announcement_source),
            and_(RagChunk.source_type == RAG_SOURCE_TASK, valid_task_source),
            and_(
                RagChunk.source_type == RAG_SOURCE_TASK_ATTACHMENT,
                valid_task_attachment_source,
            ),
            and_(RagChunk.source_type == RAG_SOURCE_RESOURCE, valid_resource_source),
            and_(RagChunk.source_type == RAG_SOURCE_COURSE, valid_course_source),
        )
        allowed_course_scope = or_(
            RagChunk.class_course_id.is_(None),
            RagChunk.class_course_id.in_(registered_class_course_ids),
            and_(representative_access, RagChunk.class_course_id.in_(active_class_course_ids)),
        )
        distance = RagChunk.embedding.cosine_distance(query_embedding).label("distance")

        return (
            select(RagChunk, distance)
            .where(
                RagChunk.classroom_id == classroom_id,
                exists(approved_membership_ids),
                allowed_course_scope,
                valid_source,
                distance <= max_distance,
            )
            .order_by(distance.asc())
            .limit(limit)
        )

    async def replace_source_chunks(
        self,
        classroom_id: int,
        class_course_id: int | None,
        source_type: str,
        source_id: int,
        chunks: list[str],
        embeddings: list[list[float]],
        source_title: str | None = None,
        page_numbers: list[int | None] | None = None,
    ) -> list[RagChunk]:
        if len(chunks) != len(embeddings):
            raise ValueError("Each chunk must have one embedding")
        if page_numbers is None:
            page_numbers = [None] * len(chunks)
        if len(page_numbers) != len(chunks):
            raise ValueError("Each chunk must have one page number value")

        await self.session.execute(
            delete(RagChunk).where(
                RagChunk.source_type == source_type,
                RagChunk.source_id == source_id,
            )
        )
        records = [
            RagChunk(
                classroom_id=classroom_id,
                class_course_id=class_course_id,
                source_type=source_type,
                source_id=source_id,
                source_title=source_title,
                page_number=page_number,
                chunk_index=index,
                content=content,
                embedding=embedding,
            )
            for index, (content, embedding, page_number) in enumerate(
                zip(chunks, embeddings, page_numbers, strict=True)
            )
        ]
        self.session.add_all(records)
        await self.session.flush()
        return records

    async def delete_source_chunks(self, source_type: str, source_id: int) -> None:
        await self.session.execute(
            delete(RagChunk).where(
                RagChunk.source_type == source_type,
                RagChunk.source_id == source_id,
            )
        )
        await self.session.flush()
