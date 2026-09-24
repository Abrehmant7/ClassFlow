import re
import logging
from dataclasses import dataclass
from datetime import datetime, timezone
from hashlib import sha256
from math import sqrt
from pathlib import Path

from fastapi import status
from sqlalchemy.ext.asyncio import AsyncSession

from app.ai.gemini_client import GeminiClient
from app.ai.loaders import (
    DocumentExtractionError,
    DocumentTooLargeError,
    extract_document_sections,
)
from app.ai.text_splitter import split_text
from app.core.config import settings
from app.core.exceptions import ClassFlowError
from app.models.announcement import Announcement
from app.models.course import ClassCourse, Course
from app.models.resource import (
    RAG_SOURCE_ANNOUNCEMENT,
    RAG_SOURCE_COURSE,
    RAG_SOURCE_RESOURCE,
    RAG_SOURCE_TASK,
    RAG_SOURCE_TASK_ATTACHMENT,
    RESOURCE_INDEX_FAILED,
    RESOURCE_INDEX_INDEXED,
    RESOURCE_INDEX_PENDING,
    RESOURCE_INDEX_PROCESSING,
    Resource,
)
from app.models.task import TASK_STATUS_ACTIVE, TASK_VISIBILITY_SHARED, Task, TaskAttachment
from app.repositories.rag import RagRepository
from app.repositories.resource import ResourceRepository
from app.schemas.chat import ChatResponse, ChatSource
from app.services.resource_storage import resource_file_path

logger = logging.getLogger(__name__)

NO_CONTEXT_ANSWER = "I could not find that information in the class materials available to you."
SOURCE_CITATION_PATTERN = re.compile(r"\[((?:\d+\s*,\s*)*\d+)\]")
ALLOWED_SOURCE_TYPES = {
    RAG_SOURCE_ANNOUNCEMENT,
    RAG_SOURCE_TASK,
    RAG_SOURCE_TASK_ATTACHMENT,
    RAG_SOURCE_RESOURCE,
    RAG_SOURCE_COURSE,
}
CHAT_FILE_CONTENT_TYPES = {
    "pdf": {"application/pdf"},
    "docx": {
        "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
        "application/octet-stream",
    },
}


@dataclass(frozen=True)
class AnswerContext:
    content: str
    source_type: str
    source_id: int | None
    source_title: str | None
    page_number: int | None
    distance: float


class RagChatService:
    def __init__(
        self,
        session: AsyncSession,
        repository: RagRepository | None = None,
        ai_client: GeminiClient | None = None,
    ) -> None:
        self.session = session
        self.repository = repository or RagRepository(session)
        self.ai_client = ai_client or GeminiClient()

    async def index_announcement(self, announcement: Announcement) -> int:
        """Stage replacement chunks in the announcement service's transaction."""
        chunks = split_text(
            f"Announcement: {announcement.title}\nBody: {announcement.body}",
            chunk_size=settings.RAG_CHUNK_SIZE,
            chunk_overlap=settings.RAG_CHUNK_OVERLAP,
        )
        embeddings = await self.ai_client.embed_documents(chunks, title=announcement.title)
        await self.repository.replace_source_chunks(
            classroom_id=announcement.classroom_id,
            class_course_id=announcement.class_course_id,
            source_type=RAG_SOURCE_ANNOUNCEMENT,
            source_id=announcement.id,
            chunks=chunks,
            embeddings=embeddings,
            source_title=announcement.title,
        )
        return len(chunks)

    async def delete_announcement(self, announcement_id: int) -> None:
        """Stage chunk deletion; the announcement service owns the commit."""
        await self.repository.delete_source_chunks(RAG_SOURCE_ANNOUNCEMENT, announcement_id)

    async def index_resource(self, resource: Resource) -> int:
        """Index a durable upload; extraction/provider failure preserves its download."""
        resource_id = resource.id
        resources = ResourceRepository(self.session)
        try:
            resource = await resources.get_by_id(resource_id, for_update=True)
            if resource is None:
                return 0
            if not resource.is_enabled:
                await self.delete_resource(resource_id)
                resource.indexing_status = RESOURCE_INDEX_PENDING
                resource.indexing_error = None
                resource.indexed_at = None
                await self.session.commit()
                return 0
            resource.indexing_status = RESOURCE_INDEX_PROCESSING
            resource.indexing_error = None
            resource.indexed_at = None
            await self.session.commit()

            # Serialize indexing with updates/deletion. Re-fetch after committing
            # processing so a concurrent deletion cannot leave orphan chunks.
            resource = await resources.get_by_id(resource_id, for_update=True)
            if resource is None:
                return 0
            if not resource.is_enabled:
                await self.session.commit()
                return 0
            with resource_file_path(resource.storage_key).open("rb") as pdf:
                file_bytes = pdf.read(settings.COURSE_RESOURCE_MAX_SIZE_BYTES + 1)
            if len(file_bytes) > settings.COURSE_RESOURCE_MAX_SIZE_BYTES:
                raise DocumentTooLargeError("Resource PDF exceeds the size limit")
            checksum = sha256(file_bytes).hexdigest()
            if resource.checksum_sha256 is not None and resource.checksum_sha256 != checksum:
                raise DocumentExtractionError("Resource PDF checksum does not match")
            sections = extract_document_sections(resource.file_name, file_bytes)
            chunks: list[str] = []
            page_numbers: list[int | None] = []
            for section in sections:
                for chunk in split_text(section.text, settings.RAG_CHUNK_SIZE, settings.RAG_CHUNK_OVERLAP):
                    context = [f"Resource: {resource.title}", f"File: {resource.file_name}"]
                    if resource.description:
                        context.append(f"Description: {resource.description}")
                    if section.page_number is not None:
                        context.append(f"Page: {section.page_number}")
                    context.append(f"Content: {chunk}")
                    chunks.append("\n".join(context))
                    page_numbers.append(section.page_number)
            if not chunks:
                raise DocumentExtractionError("Resource contains no extractable text")
            embeddings = await self.ai_client.embed_documents(chunks, title=resource.title)
            await self.repository.replace_source_chunks(
                classroom_id=resource.classroom_id,
                class_course_id=resource.class_course_id,
                source_type=RAG_SOURCE_RESOURCE,
                source_id=resource_id,
                chunks=chunks,
                embeddings=embeddings,
                source_title=resource.title,
                page_numbers=page_numbers,
            )
            resource.indexing_status = RESOURCE_INDEX_INDEXED
            resource.indexing_error = None
            resource.indexed_at = datetime.now(timezone.utc)
            resource.file_size = len(file_bytes)
            resource.checksum_sha256 = checksum
            await self.session.commit()
            return len(chunks)
        except Exception as exc:
            await self.session.rollback()
            resource = await resources.get_by_id(resource_id, for_update=True)
            if resource is None:
                return 0
            await self.delete_resource(resource_id)
            resource.indexing_status = RESOURCE_INDEX_FAILED
            resource.indexed_at = None
            resource.indexing_error = self._resource_indexing_error(exc)
            await self.session.commit()
            # Provider exceptions may contain keys, response bodies, or paths.
            logger.warning("Resource %s indexing failed (%s)", resource_id, type(exc).__name__)
            return 0

    async def delete_resource(self, resource_id: int) -> None:
        """Stage chunk deletion; the resource service owns the enclosing commit."""
        await self.repository.delete_source_chunks(RAG_SOURCE_RESOURCE, resource_id)

    @staticmethod
    def _resource_indexing_error(exc: Exception) -> str:
        if isinstance(exc, DocumentTooLargeError):
            return "The PDF exceeds the indexing limits. Upload a smaller document."
        if isinstance(exc, DocumentExtractionError):
            return "The PDF could not be read. Upload an unencrypted PDF containing extractable text."
        if isinstance(exc, OSError):
            return "The PDF file could not be read from storage."
        return "Resource indexing failed. Please retry later."

    async def answer_class_question(
        self,
        classroom_id: int,
        user_id: int,
        question: str,
    ) -> ChatResponse:
        normalized_question = question.strip()
        if not normalized_question:
            raise ClassFlowError(
                "Chat message is required",
                "CHAT_MESSAGE_REQUIRED",
                status.HTTP_422_UNPROCESSABLE_CONTENT,
            )

        query_embedding = await self.ai_client.embed_query(normalized_question)
        matches = await self.repository.search_accessible(
            classroom_id=classroom_id,
            user_id=user_id,
            query_embedding=query_embedding,
            limit=settings.RAG_TOP_K,
            max_distance=settings.RAG_MAX_DISTANCE,
        )
        if not matches:
            return ChatResponse(answer=NO_CONTEXT_ANSWER, sources=[])

        contexts = [
            AnswerContext(
                content=match.chunk.content,
                source_type=match.chunk.source_type,
                source_id=match.chunk.source_id,
                source_title=match.chunk.source_title,
                page_number=match.chunk.page_number,
                distance=match.distance,
            )
            for match in matches
        ]
        return await self._generate_response(normalized_question, contexts)

    async def answer_class_question_with_file(
        self,
        classroom_id: int,
        user_id: int,
        question: str,
        file_name: str,
        content_type: str | None,
        file_bytes: bytes,
    ) -> ChatResponse:
        normalized_question = question.strip()
        if not normalized_question:
            raise ClassFlowError(
                "Chat message is required",
                "CHAT_MESSAGE_REQUIRED",
                status.HTTP_422_UNPROCESSABLE_CONTENT,
            )

        if not await self.repository.user_has_approved_class_access(
            classroom_id,
            user_id,
        ):
            raise ClassFlowError(
                "Approved class membership required",
                "APPROVED_CLASS_MEMBERSHIP_REQUIRED",
                status.HTTP_403_FORBIDDEN,
            )

        safe_file_name, _extension = self._validate_chat_file(
            file_name,
            content_type,
            file_bytes,
        )
        try:
            sections = extract_document_sections(
                safe_file_name,
                file_bytes,
                max_pages=settings.RAG_CHAT_FILE_MAX_PAGES,
                max_characters=settings.RAG_CHAT_FILE_MAX_EXTRACTED_CHARACTERS,
            )
        except DocumentTooLargeError as exc:
            raise ClassFlowError(
                str(exc),
                "CHAT_FILE_TOO_LARGE",
                status.HTTP_413_CONTENT_TOO_LARGE,
            ) from exc
        except DocumentExtractionError as exc:
            raise ClassFlowError(
                str(exc),
                "CHAT_FILE_EXTRACTION_FAILED",
                status.HTTP_422_UNPROCESSABLE_CONTENT,
            ) from exc

        file_chunks: list[tuple[str, int | None]] = []
        for section in sections:
            section_chunks = split_text(
                section.text,
                chunk_size=settings.RAG_CHUNK_SIZE,
                chunk_overlap=settings.RAG_CHUNK_OVERLAP,
            )
            file_chunks.extend(
                (chunk, section.page_number) for chunk in section_chunks
            )

        if len(file_chunks) > settings.RAG_CHAT_FILE_MAX_CHUNKS:
            raise ClassFlowError(
                "The document produces too many chunks to process",
                "CHAT_FILE_TOO_LARGE",
                status.HTTP_413_CONTENT_TOO_LARGE,
            )

        query_embedding = await self.ai_client.embed_query(normalized_question)
        file_embeddings = await self.ai_client.embed_documents(
            [chunk for chunk, _page_number in file_chunks],
            title=safe_file_name,
        )
        file_contexts = [
            AnswerContext(
                content=self._file_context_content(
                    safe_file_name,
                    chunk,
                    page_number,
                ),
                source_type="uploaded_file",
                source_id=None,
                source_title=safe_file_name,
                page_number=page_number,
                distance=self._cosine_distance(query_embedding, embedding),
            )
            for (chunk, page_number), embedding in zip(
                file_chunks,
                file_embeddings,
                strict=True,
            )
        ]
        file_contexts = [
            context
            for context in file_contexts
            if context.distance <= settings.RAG_MAX_DISTANCE
        ]

        class_matches = await self.repository.search_accessible(
            classroom_id=classroom_id,
            user_id=user_id,
            query_embedding=query_embedding,
            limit=settings.RAG_TOP_K,
            max_distance=settings.RAG_MAX_DISTANCE,
        )
        class_contexts = [
            AnswerContext(
                content=match.chunk.content,
                source_type=match.chunk.source_type,
                source_id=match.chunk.source_id,
                source_title=match.chunk.source_title,
                page_number=match.chunk.page_number,
                distance=match.distance,
            )
            for match in class_matches
        ]
        file_contexts.sort(key=lambda context: context.distance)
        class_contexts.sort(key=lambda context: context.distance)
        contexts = (
            file_contexts[: settings.RAG_TOP_K]
            if file_contexts
            else class_contexts[: settings.RAG_TOP_K]
        )
        if not contexts:
            return ChatResponse(answer=NO_CONTEXT_ANSWER, sources=[])

        return await self._generate_response(normalized_question, contexts)

    async def _generate_response(
        self,
        question: str,
        contexts: list[AnswerContext],
    ) -> ChatResponse:
        answer = await self.ai_client.generate_answer(
            question,
            [context.content for context in contexts],
        )
        cited_contexts = self._cited_contexts(answer, contexts)
        sources: list[ChatSource] = []
        seen_sources: set[tuple[str, int | None, str | None, int | None]] = set()
        for context in cited_contexts:
            source_key = (
                context.source_type,
                context.source_id,
                context.source_title,
                context.page_number,
            )
            if source_key in seen_sources:
                continue
            seen_sources.add(source_key)
            sources.append(
                ChatSource(
                    source_type=context.source_type,
                    source_id=context.source_id,
                    title=context.source_title,
                    page_number=context.page_number,
                    preview=self._preview(context.content),
                )
            )

        return ChatResponse(answer=answer, sources=sources)

    @staticmethod
    def _cited_contexts(
        answer: str,
        contexts: list[AnswerContext],
    ) -> list[AnswerContext]:
        cited_contexts: list[AnswerContext] = []
        seen_indexes: set[int] = set()
        for citation_group in SOURCE_CITATION_PATTERN.findall(answer):
            for value in citation_group.split(","):
                context_index = int(value.strip()) - 1
                if context_index < 0 or context_index >= len(contexts):
                    continue
                if context_index in seen_indexes:
                    continue
                seen_indexes.add(context_index)
                cited_contexts.append(contexts[context_index])
        return cited_contexts

    @staticmethod
    def _validate_chat_file(
        file_name: str,
        content_type: str | None,
        file_bytes: bytes,
    ) -> tuple[str, str]:
        safe_file_name = file_name.replace("\\", "/").rsplit("/", 1)[-1].strip()
        if not safe_file_name or safe_file_name != file_name:
            raise ClassFlowError(
                "Invalid chat attachment filename",
                "CHAT_FILE_INVALID_NAME",
                status.HTTP_422_UNPROCESSABLE_CONTENT,
            )

        extension = Path(safe_file_name).suffix.lower().lstrip(".")
        allowed_content_types = CHAT_FILE_CONTENT_TYPES.get(extension)
        if allowed_content_types is None or content_type not in allowed_content_types:
            raise ClassFlowError(
                "Only PDF and DOCX chat attachments are supported",
                "CHAT_FILE_TYPE_NOT_ALLOWED",
                status.HTTP_422_UNPROCESSABLE_CONTENT,
            )
        if not file_bytes:
            raise ClassFlowError(
                "The chat attachment is empty",
                "CHAT_FILE_EMPTY",
                status.HTTP_422_UNPROCESSABLE_CONTENT,
            )
        if len(file_bytes) > settings.RAG_CHAT_FILE_MAX_SIZE_BYTES:
            raise ClassFlowError(
                "The chat attachment exceeds the size limit",
                "CHAT_FILE_TOO_LARGE",
                status.HTTP_413_CONTENT_TOO_LARGE,
            )
        if extension == "pdf" and b"%PDF-" not in file_bytes[:1024]:
            raise ClassFlowError(
                "The uploaded file is not a valid PDF",
                "CHAT_FILE_EXTRACTION_FAILED",
                status.HTTP_422_UNPROCESSABLE_CONTENT,
            )
        return safe_file_name, extension

    @staticmethod
    def _file_context_content(
        file_name: str,
        content: str,
        page_number: int | None,
    ) -> str:
        page_label = f"\nPage: {page_number}" if page_number is not None else ""
        return f"Uploaded file: {file_name}{page_label}\nContent: {content}"

    @staticmethod
    def _cosine_distance(left: list[float], right: list[float]) -> float:
        if len(left) != len(right):
            raise ValueError("Embedding dimensions must match")
        left_norm = sqrt(sum(value * value for value in left))
        right_norm = sqrt(sum(value * value for value in right))
        if left_norm == 0 or right_norm == 0:
            return 1.0
        similarity = sum(a * b for a, b in zip(left, right, strict=True)) / (
            left_norm * right_norm
        )
        return 1.0 - similarity

    async def index_source(
        self,
        classroom_id: int,
        class_course_id: int | None,
        source_type: str,
        source_id: int,
        text: str,
        title: str | None = None,
        *,
        commit: bool = True,
    ) -> int:
        if source_type not in ALLOWED_SOURCE_TYPES:
            raise ValueError("Unsupported RAG source type")

        chunks = split_text(
            text,
            chunk_size=settings.RAG_CHUNK_SIZE,
            chunk_overlap=settings.RAG_CHUNK_OVERLAP,
        )
        if not chunks:
            await self.repository.delete_source_chunks(source_type, source_id)
            if commit:
                await self.session.commit()
            return 0

        return await self._index_chunks(
            classroom_id=classroom_id,
            class_course_id=class_course_id,
            source_type=source_type,
            source_id=source_id,
            chunks=chunks,
            source_title=title,
            page_numbers=[None] * len(chunks),
            commit=commit,
        )

    async def _index_chunks(
        self,
        classroom_id: int,
        class_course_id: int | None,
        source_type: str,
        source_id: int,
        chunks: list[str],
        source_title: str | None,
        page_numbers: list[int | None],
        *,
        commit: bool = True,
    ) -> int:
        embeddings = await self.ai_client.embed_documents(chunks, title=source_title)
        await self.repository.replace_source_chunks(
            classroom_id=classroom_id,
            class_course_id=class_course_id,
            source_type=source_type,
            source_id=source_id,
            chunks=chunks,
            embeddings=embeddings,
            source_title=source_title,
            page_numbers=page_numbers,
        )
        if commit:
            await self.session.commit()
        return len(chunks)

    async def index_task_attachment(
        self,
        task: Task,
        attachment: TaskAttachment,
        file_bytes: bytes,
    ) -> int:
        if task.visibility != TASK_VISIBILITY_SHARED or task.status != TASK_STATUS_ACTIVE:
            await self.delete_task_attachment(attachment.id)
            return 0

        try:
            sections = extract_document_sections(attachment.file_name, file_bytes)
        except DocumentExtractionError as exc:
            raise ClassFlowError(
                str(exc),
                "ATTACHMENT_TEXT_EXTRACTION_FAILED",
                status.HTTP_422_UNPROCESSABLE_CONTENT,
            ) from exc

        if not sections:
            await self.delete_task_attachment(attachment.id)
            return 0

        chunks: list[str] = []
        page_numbers: list[int | None] = []
        for section in sections:
            section_chunks = split_text(
                section.text,
                chunk_size=settings.RAG_CHUNK_SIZE,
                chunk_overlap=settings.RAG_CHUNK_OVERLAP,
            )
            for section_chunk in section_chunks:
                page_label = (
                    f"\nPage: {section.page_number}"
                    if section.page_number is not None
                    else ""
                )
                chunks.append(
                    f"Task: {task.title}\n"
                    f"Attachment: {attachment.file_name}"
                    f"{page_label}\n"
                    f"Content: {section_chunk}"
                )
                page_numbers.append(section.page_number)

        return await self._index_chunks(
            classroom_id=task.classroom_id,
            class_course_id=task.class_course_id,
            source_type=RAG_SOURCE_TASK_ATTACHMENT,
            source_id=attachment.id,
            chunks=chunks,
            source_title=attachment.file_name,
            page_numbers=page_numbers,
        )

    async def delete_task_attachment(self, attachment_id: int) -> None:
        await self.repository.delete_source_chunks(
            RAG_SOURCE_TASK_ATTACHMENT,
            attachment_id,
        )
        await self.session.commit()

    async def index_task(self, task: Task, *, commit: bool = True) -> int:
        if task.visibility != TASK_VISIBILITY_SHARED or task.status != TASK_STATUS_ACTIVE:
            await self.repository.delete_source_chunks(RAG_SOURCE_TASK, task.id)
            if commit:
                await self.session.commit()
            return 0

        deadline = task.deadline.isoformat() if task.deadline is not None else "No deadline"
        text = "\n".join(
            part
            for part in (
                f"Task title: {task.title}",
                f"Task type: {task.task_type}",
                f"Priority: {task.priority}",
                f"Deadline: {deadline}",
                f"Description: {task.description}" if task.description else None,
            )
            if part is not None
        )
        return await self.index_source(
            classroom_id=task.classroom_id,
            class_course_id=task.class_course_id,
            source_type=RAG_SOURCE_TASK,
            source_id=task.id,
            text=text,
            title=task.title,
            commit=commit,
        )

    async def index_class_course(
        self,
        class_course: ClassCourse,
        course: Course | None = None,
    ) -> int:
        if not class_course.is_active:
            await self.repository.delete_source_chunks(RAG_SOURCE_COURSE, class_course.id)
            await self.session.commit()
            return 0

        course = course or class_course.course
        text = "\n".join(
            part
            for part in (
                f"Course name: {course.name}",
                f"Course code: {course.code}",
                f"Instructor: {class_course.instructor_name}" if class_course.instructor_name else None,
                f"Course description: {course.description}" if course.description else None,
            )
            if part is not None
        )
        return await self.index_source(
            classroom_id=class_course.classroom_id,
            class_course_id=class_course.id,
            source_type=RAG_SOURCE_COURSE,
            source_id=class_course.id,
            text=text,
            title=course.name,
        )

    async def reindex_class_sources(self, classroom_id: int) -> tuple[int, int, int]:
        tasks = await self.repository.list_indexable_tasks(classroom_id)
        class_courses = await self.repository.list_indexable_class_courses(classroom_id)
        attachment_sources = await self.repository.list_indexable_task_attachments(classroom_id)

        for task in tasks:
            await self.index_task(task)
        for class_course in class_courses:
            await self.index_class_course(class_course)
        indexed_attachments = 0
        for attachment_source in attachment_sources:
            file_path = self._attachment_path(attachment_source.attachment.storage_key)
            if not file_path.is_file():
                await self.delete_task_attachment(attachment_source.attachment.id)
                continue
            chunk_count = await self.index_task_attachment(
                attachment_source.task,
                attachment_source.attachment,
                file_path.read_bytes(),
            )
            if chunk_count > 0:
                indexed_attachments += 1

        return len(tasks), len(class_courses), indexed_attachments

    @staticmethod
    def _attachment_path(storage_key: str) -> Path:
        storage_root = Path(settings.TASK_ATTACHMENT_STORAGE_DIR)
        if not storage_root.is_absolute():
            storage_root = Path.cwd() / storage_root
        storage_root = storage_root.resolve()
        file_path = (storage_root / storage_key).resolve()
        if storage_root not in file_path.parents and file_path != storage_root:
            raise ClassFlowError(
                "Invalid attachment storage key",
                "INVALID_ATTACHMENT_STORAGE_KEY",
                status.HTTP_500_INTERNAL_SERVER_ERROR,
            )
        return file_path

    @staticmethod
    def _preview(content: str, max_length: int = 240) -> str:
        normalized = re.sub(r"\s+", " ", content).strip()
        if len(normalized) <= max_length:
            return normalized
        return normalized[: max_length - 3].rstrip() + "..."
