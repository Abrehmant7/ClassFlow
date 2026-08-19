from datetime import datetime, timezone
from pathlib import Path
from uuid import uuid4

from fastapi import UploadFile, status

from app.core.config import settings
from app.core.exceptions import ClassFlowError
from app.models.classroom import CLASS_ROLE_REPRESENTATIVE, MEMBERSHIP_STATUS_APPROVED, ClassMembership
from app.models.course import ClassCourse
from app.models.task import (
    TASK_PROGRESS_COMPLETED,
    TASK_PROGRESS_PENDING,
    TASK_STATUS_ACTIVE,
    TASK_STATUS_ARCHIVED,
    TASK_STATUS_CANCELLED,
    TASK_STATUS_COMPLETED,
    TASK_VISIBILITY_PERSONAL,
    TASK_VISIBILITY_SHARED,
    Task,
    TaskAttachment,
    TaskProgress,
)
from app.repositories.course import ClassCourseRepository, CourseRegistrationRepository
from app.repositories.membership import ClassMembershipRepository
from app.repositories.task import TaskAttachmentRepository, TaskProgressRepository, TaskRepository
from app.schemas.task import (
    TaskAttachmentDownload,
    TaskAttachmentRead,
    TaskCourseRead,
    TaskCreate,
    TaskCreatorRead,
    TaskListItem,
    TaskProgressRead,
    TaskProgressUpdate,
    TaskRead,
    TaskUpdate,
)


class TaskService:
    def __init__(
        self,
        task_repository: TaskRepository,
        progress_repository: TaskProgressRepository,
        attachment_repository: TaskAttachmentRepository,
        membership_repository: ClassMembershipRepository,
        class_course_repository: ClassCourseRepository,
        registration_repository: CourseRegistrationRepository,
    ) -> None:
        self.task_repository = task_repository
        self.progress_repository = progress_repository
        self.attachment_repository = attachment_repository
        self.membership_repository = membership_repository
        self.class_course_repository = class_course_repository
        self.registration_repository = registration_repository
        self.session = task_repository.session

    async def create_class_task(self, classroom_id: int, task_in: TaskCreate, user_id: int) -> TaskRead:
        """Create a task from a class screen, using the path classroom as the relationship."""
        if task_in.classroom_id is not None and task_in.classroom_id != classroom_id:
            raise ClassFlowError("Task classroom does not match route", "TASK_CLASSROOM_MISMATCH", status.HTTP_422_UNPROCESSABLE_CONTENT)

        return await self._create_task(classroom_id=classroom_id, task_in=task_in, user_id=user_id)

    async def create_personal_task(self, task_in: TaskCreate, user_id: int) -> TaskRead:
        """Create an owner-only personal task that may have no class or course link."""
        if task_in.visibility != TASK_VISIBILITY_PERSONAL:
            raise ClassFlowError("Only personal tasks can be created here", "PERSONAL_TASK_REQUIRED", status.HTTP_422_UNPROCESSABLE_CONTENT)

        return await self._create_task(classroom_id=task_in.classroom_id, task_in=task_in, user_id=user_id)

    async def complete_personal_task(self, task_id: int, user_id: int) -> TaskRead:
        """Idempotently complete a personal task without deleting or archiving it."""
        task = await self._get_task_or_404(task_id)
        membership = await self._get_membership_for_task(task, user_id)
        await self._require_can_manage_task(task, membership, user_id)
        self._require_personal_task(task)

        if task.status != TASK_STATUS_COMPLETED or task.completed_at is None:
            task.status = TASK_STATUS_COMPLETED
            task.completed_at = datetime.now(timezone.utc)
            await self.session.flush()
            await self.session.commit()

        task = await self._get_task_or_404(task.id)
        return await self._build_task_read(task, membership, user_id, include_attachments=True)

    async def reopen_personal_task(self, task_id: int, user_id: int) -> TaskRead:
        """Idempotently reopen a personal task by clearing its completion timestamp."""
        task = await self._get_task_or_404(task_id)
        membership = await self._get_membership_for_task(task, user_id)
        await self._require_can_manage_task(task, membership, user_id)
        self._require_personal_task(task)

        if task.status != TASK_STATUS_ACTIVE or task.completed_at is not None:
            task.status = TASK_STATUS_ACTIVE
            task.completed_at = None
            await self.session.flush()
            await self.session.commit()

        task = await self._get_task_or_404(task.id)
        return await self._build_task_read(task, membership, user_id, include_attachments=True)

    async def _create_task(self, classroom_id: int | None, task_in: TaskCreate, user_id: int) -> TaskRead:
        if task_in.visibility == TASK_VISIBILITY_SHARED:
            if classroom_id is None:
                raise ClassFlowError("Shared tasks require a classroom", "SHARED_TASK_CLASSROOM_REQUIRED", status.HTTP_422_UNPROCESSABLE_CONTENT)

            membership = await self._require_approved_membership(user_id, classroom_id)
            self._require_representative_membership(membership)
            await self._validate_shared_task_course(classroom_id, task_in.class_course_id)
        elif task_in.visibility == TASK_VISIBILITY_PERSONAL:
            membership = await self._validate_personal_task_links(user_id, classroom_id, task_in.class_course_id)
        else:
            raise ClassFlowError("Invalid task visibility", "INVALID_TASK_VISIBILITY", status.HTTP_422_UNPROCESSABLE_CONTENT)

        task = await self.task_repository.create(
            classroom_id=classroom_id,
            task_in=task_in,
            created_by_user_id=user_id,
        )
        await self.session.commit()

        task = await self._get_task_or_404(task.id)
        return await self._build_task_read(task, membership, user_id, include_attachments=True)

    async def list_tasks(
        self,
        classroom_id: int,
        user_id: int,
        include_closed: bool = False,
    ) -> list[TaskListItem]:
        """Return shared class tasks plus the current user's personal tasks linked to that class."""
        membership = await self._require_approved_membership(user_id, classroom_id)
        is_representative = self._is_representative(membership)

        if include_closed and not is_representative:
            raise ClassFlowError("Class representative access required", "CLASS_REPRESENTATIVE_REQUIRED", status.HTTP_403_FORBIDDEN)

        tasks = await self.task_repository.list_accessible_for_class(
            classroom_id=classroom_id,
            user_id=user_id,
            membership_id=membership.id,
            is_representative=is_representative,
            include_closed=include_closed,
        )

        return [
            await self._build_task_list_item(task, membership, user_id)
            for task in tasks
        ]

    async def list_feed_tasks(self, user_id: int, include_closed: bool = False) -> list[TaskListItem]:
        """Return the personal feed: owner personal tasks plus accessible shared tasks."""
        tasks = await self.task_repository.list_feed_for_user(user_id=user_id, include_closed=include_closed)
        items: list[TaskListItem] = []

        for task in tasks:
            membership = await self._get_membership_for_task(task, user_id)
            items.append(await self._build_task_list_item(task, membership, user_id))

        return items

    async def get_task(self, task_id: int, user_id: int) -> TaskRead:
        """Return one task only if it is shared with the user or owned by the user."""
        task = await self._get_task_or_404(task_id)
        membership = await self._get_membership_for_task(task, user_id)
        await self._require_can_view_task(task, membership, user_id)

        return await self._build_task_read(task, membership, user_id, include_attachments=True)

    async def update_task(self, task_id: int, task_in: TaskUpdate, user_id: int) -> TaskRead:
        """Apply the different shared/personal task update rules."""
        task = await self._get_task_or_404(task_id)
        membership = await self._get_membership_for_task(task, user_id)
        await self._require_can_manage_task(task, membership, user_id)

        update_data = task_in.model_dump(exclude_unset=True)
        if not update_data:
            return await self._build_task_read(task, membership, user_id, include_attachments=True)

        if task.visibility == TASK_VISIBILITY_SHARED:
            self._validate_shared_task_update(update_data)
            if update_data.get("status") == TASK_STATUS_ACTIVE:
                task.completed_at = None
        else:
            self._validate_personal_task_update(update_data)
            self._apply_personal_completion_timestamp(task, update_data.get("status"))

        task = await self.task_repository.update(task, task_in)
        await self.session.commit()

        task = await self._get_task_or_404(task.id)
        return await self._build_task_read(task, membership, user_id, include_attachments=True)

    async def delete_task(self, task_id: int, user_id: int) -> None:
        """Delete only personal tasks when the creator explicitly asks for deletion."""
        task = await self._get_task_or_404(task_id)
        membership = await self._get_membership_for_task(task, user_id)
        await self._require_can_manage_task(task, membership, user_id)

        if task.visibility != TASK_VISIBILITY_PERSONAL:
            raise ClassFlowError("Shared tasks cannot be deleted", "SHARED_TASK_DELETE_NOT_ALLOWED", status.HTTP_403_FORBIDDEN)

        attachment_paths = [self._attachment_path(attachment.storage_key) for attachment in task.attachments]
        await self.task_repository.delete(task)
        await self.session.commit()

        for attachment_path in attachment_paths:
            self._delete_file_if_present(attachment_path)

    async def update_progress(self, task_id: int, progress_in: TaskProgressUpdate, user_id: int) -> TaskRead:
        """Upsert the authenticated member's progress row for a shared task."""
        task = await self._get_task_or_404(task_id)
        self._require_active_task_class_course(task)
        membership = await self._get_membership_for_task(task, user_id)

        if task.visibility != TASK_VISIBILITY_SHARED:
            raise ClassFlowError("Only shared tasks use progress records", "TASK_PROGRESS_NOT_ALLOWED", status.HTTP_409_CONFLICT)

        if membership is None:
            raise ClassFlowError("Approved class membership required", "APPROVED_CLASS_MEMBERSHIP_REQUIRED", status.HTTP_403_FORBIDDEN)

        if task.status in {TASK_STATUS_CANCELLED, TASK_STATUS_ARCHIVED}:
            raise ClassFlowError("Closed tasks cannot receive progress updates", "TASK_CLOSED_FOR_PROGRESS", status.HTTP_409_CONFLICT)

        await self._require_task_progress_audience(task, membership)

        completed_at = datetime.now(timezone.utc) if progress_in.status == TASK_PROGRESS_COMPLETED else None
        await self.progress_repository.upsert_for_membership(
            task_id=task.id,
            membership_id=membership.id,
            progress_status=progress_in.status,
            completed_at=completed_at,
        )
        await self.session.commit()

        task = await self._get_task_or_404(task.id)
        return await self._build_task_read(task, membership, user_id, include_attachments=True)

    async def upload_attachment(self, task_id: int, user_id: int, file: UploadFile) -> TaskAttachmentRead:
        """Store one supporting file after checking task management permissions."""
        task = await self._get_task_or_404(task_id)
        membership = await self._get_membership_for_task(task, user_id)
        await self._require_can_manage_attachment(task, membership, user_id)

        file_name, extension = self._validate_attachment_name(file.filename)
        file_type = self._validate_attachment_content_type(file.content_type)
        file_bytes = await self._read_validated_attachment_bytes(file)

        storage_key = f"tasks/{task.id}/{uuid4().hex}.{extension}"
        file_path = self._attachment_path(storage_key)

        try:
            file_path.parent.mkdir(parents=True, exist_ok=True)
            file_path.write_bytes(file_bytes)
        except OSError as exc:
            raise ClassFlowError("Could not store attachment file", "ATTACHMENT_STORAGE_FAILED", status.HTTP_500_INTERNAL_SERVER_ERROR) from exc

        try:
            attachment = await self.attachment_repository.create(
                task_id=task.id,
                uploaded_by_user_id=user_id,
                file_name=file_name,
                storage_key=storage_key,
                file_type=file_type,
                file_size=len(file_bytes),
            )
            await self.session.commit()
            return TaskAttachmentRead.model_validate(attachment)
        except Exception:
            await self.session.rollback()
            self._delete_file_if_present(file_path)
            raise

    async def list_attachments(self, task_id: int, user_id: int) -> list[TaskAttachmentRead]:
        """List attachments only after task visibility has been verified."""
        task = await self._get_task_or_404(task_id)
        membership = await self._get_membership_for_task(task, user_id)
        await self._require_can_view_task(task, membership, user_id)

        attachments = await self.attachment_repository.list_for_task(task.id)
        return [TaskAttachmentRead.model_validate(attachment) for attachment in attachments]

    async def get_attachment_download(self, attachment_id: int, user_id: int) -> TaskAttachmentDownload:
        """Resolve an attachment to a local file only for users who can view its task."""
        attachment = await self._get_attachment_or_404(attachment_id)
        task = attachment.task
        membership = await self._get_membership_for_task(task, user_id)
        await self._require_can_view_task(task, membership, user_id)

        file_path = self._attachment_path(attachment.storage_key)
        if not file_path.exists() or not file_path.is_file():
            raise ClassFlowError("Attachment file not found", "ATTACHMENT_FILE_NOT_FOUND", status.HTTP_404_NOT_FOUND)

        return TaskAttachmentDownload(
            file_path=str(file_path),
            file_name=attachment.file_name,
            file_type=attachment.file_type,
        )

    async def delete_attachment(self, attachment_id: int, user_id: int) -> None:
        """Delete an attachment record and remove its file for task managers only."""
        attachment = await self._get_attachment_or_404(attachment_id)
        task = attachment.task
        membership = await self._get_membership_for_task(task, user_id)
        await self._require_can_manage_attachment(task, membership, user_id)

        file_path = self._attachment_path(attachment.storage_key)
        await self.attachment_repository.delete(attachment)
        await self.session.commit()
        self._delete_file_if_present(file_path)

    async def _get_task_or_404(self, task_id: int) -> Task:
        task = await self.task_repository.get_by_id(task_id)

        if task is None:
            raise ClassFlowError("Task not found", "TASK_NOT_FOUND", status.HTTP_404_NOT_FOUND)

        return task

    async def _get_attachment_or_404(self, attachment_id: int) -> TaskAttachment:
        attachment = await self.attachment_repository.get_by_id(attachment_id)

        if attachment is None:
            raise ClassFlowError("Attachment not found", "ATTACHMENT_NOT_FOUND", status.HTTP_404_NOT_FOUND)

        return attachment

    async def _get_membership_for_task(self, task: Task, user_id: int) -> ClassMembership | None:
        if task.classroom_id is None:
            return None

        return await self.membership_repository.get_by_user_and_class(
            user_id=user_id,
            classroom_id=task.classroom_id,
        )

    async def _require_can_view_task(self, task: Task, membership: ClassMembership | None, user_id: int) -> None:
        self._require_active_task_class_course(task)

        if task.visibility == TASK_VISIBILITY_PERSONAL:
            if task.created_by_user_id != user_id:
                raise ClassFlowError("Task not found", "TASK_NOT_FOUND", status.HTTP_404_NOT_FOUND)
            return

        if task.visibility == TASK_VISIBILITY_SHARED:
            if task.classroom_id is None:
                raise ClassFlowError("Task not found", "TASK_NOT_FOUND", status.HTTP_404_NOT_FOUND)

            membership = self._require_approved_membership_object(membership)

            if self._is_representative(membership):
                return

            if task.class_course_id is None:
                return

            await self._require_active_course_registration(membership.id, task.class_course_id)
            return

        raise ClassFlowError("Task not found", "TASK_NOT_FOUND", status.HTTP_404_NOT_FOUND)

    async def _require_can_manage_task(self, task: Task, membership: ClassMembership | None, user_id: int) -> None:
        self._require_active_task_class_course(task)

        if task.visibility == TASK_VISIBILITY_SHARED:
            membership = self._require_approved_membership_object(membership)
            self._require_representative_membership(membership)
            return

        if task.created_by_user_id == user_id:
            return

        raise ClassFlowError("Task management access required", "TASK_MANAGEMENT_REQUIRED", status.HTTP_403_FORBIDDEN)

    async def _require_can_manage_attachment(self, task: Task, membership: ClassMembership | None, user_id: int) -> None:
        self._require_active_task_class_course(task)

        if task.visibility == TASK_VISIBILITY_SHARED:
            membership = self._require_approved_membership_object(membership)
            self._require_representative_membership(membership)
            return

        if task.created_by_user_id == user_id:
            return

        raise ClassFlowError("Attachment management access required", "ATTACHMENT_MANAGEMENT_REQUIRED", status.HTTP_403_FORBIDDEN)

    def _require_personal_task(self, task: Task) -> None:
        if task.visibility != TASK_VISIBILITY_PERSONAL:
            raise ClassFlowError("Personal task required", "PERSONAL_TASK_REQUIRED", status.HTTP_409_CONFLICT)

    def _require_active_task_class_course(self, task: Task) -> None:
        if (
            task.class_course_id is not None
            and task.class_course is not None
            and not task.class_course.is_active
        ):
            raise ClassFlowError("Task not found", "TASK_NOT_FOUND", status.HTTP_404_NOT_FOUND)

    async def _validate_personal_task_links(
        self,
        user_id: int,
        classroom_id: int | None,
        class_course_id: int | None,
    ) -> ClassMembership | None:
        if class_course_id is not None and classroom_id is None:
            raise ClassFlowError("Course-linked personal tasks require a classroom", "TASK_COURSE_REQUIRES_CLASSROOM", status.HTTP_422_UNPROCESSABLE_CONTENT)

        if classroom_id is None:
            return None

        membership = await self._require_approved_membership(user_id, classroom_id)

        if class_course_id is not None:
            class_course = await self._get_active_class_course_for_class(classroom_id, class_course_id)
            await self._require_active_course_registration(membership.id, class_course.id)

        return membership

    async def _require_task_progress_audience(self, task: Task, membership: ClassMembership) -> None:
        if task.class_course_id is not None:
            await self._require_active_course_registration(membership.id, task.class_course_id)

    async def _require_approved_membership(self, user_id: int, classroom_id: int) -> ClassMembership:
        membership = await self.membership_repository.get_by_user_and_class(
            user_id=user_id,
            classroom_id=classroom_id,
        )

        return self._require_approved_membership_object(membership)

    def _require_approved_membership_object(self, membership: ClassMembership | None) -> ClassMembership:
        if membership is None or membership.status != MEMBERSHIP_STATUS_APPROVED:
            raise ClassFlowError("Approved class membership required", "APPROVED_CLASS_MEMBERSHIP_REQUIRED", status.HTTP_403_FORBIDDEN)

        return membership

    def _require_representative_membership(self, membership: ClassMembership) -> None:
        if not self._is_representative(membership):
            raise ClassFlowError("Class representative access required", "CLASS_REPRESENTATIVE_REQUIRED", status.HTTP_403_FORBIDDEN)

    def _is_representative(self, membership: ClassMembership) -> bool:
        return membership.status == MEMBERSHIP_STATUS_APPROVED and membership.role == CLASS_ROLE_REPRESENTATIVE

    async def _validate_shared_task_course(self, classroom_id: int, class_course_id: int | None) -> None:
        if class_course_id is None:
            return

        await self._get_active_class_course_for_class(classroom_id, class_course_id)

    async def _get_active_class_course_for_class(self, classroom_id: int, class_course_id: int) -> ClassCourse:
        class_course = await self.class_course_repository.get_by_id(class_course_id)

        if class_course is None or class_course.classroom_id != classroom_id:
            raise ClassFlowError("Class course not found", "CLASS_COURSE_NOT_FOUND", status.HTTP_404_NOT_FOUND)

        if not class_course.is_active:
            raise ClassFlowError("Class course is inactive", "CLASS_COURSE_INACTIVE", status.HTTP_409_CONFLICT)

        return class_course

    async def _require_active_course_registration(self, membership_id: int, class_course_id: int) -> None:
        registration = await self.registration_repository.get_by_membership_and_class_course(
            membership_id=membership_id,
            class_course_id=class_course_id,
        )

        if registration is None or not registration.is_active:
            raise ClassFlowError("Active course registration required", "COURSE_REGISTRATION_REQUIRED", status.HTTP_403_FORBIDDEN)

    def _validate_shared_task_update(self, update_data: dict) -> None:
        allowed_fields = {"title", "description", "deadline", "priority", "status"}
        disallowed_fields = set(update_data) - allowed_fields

        if disallowed_fields:
            raise ClassFlowError("Shared task field cannot be updated", "SHARED_TASK_FIELD_NOT_ALLOWED", status.HTTP_422_UNPROCESSABLE_CONTENT)

        if update_data.get("status") == TASK_STATUS_COMPLETED:
            raise ClassFlowError("Shared tasks cannot be completed directly", "SHARED_TASK_COMPLETED_NOT_ALLOWED", status.HTTP_409_CONFLICT)

    def _validate_personal_task_update(self, update_data: dict) -> None:
        allowed_fields = {"title", "description", "deadline", "priority", "task_type", "status"}
        disallowed_fields = set(update_data) - allowed_fields

        if disallowed_fields:
            raise ClassFlowError("Personal task field cannot be updated", "PERSONAL_TASK_FIELD_NOT_ALLOWED", status.HTTP_422_UNPROCESSABLE_CONTENT)

        if update_data.get("status") == TASK_STATUS_CANCELLED:
            raise ClassFlowError("Personal tasks cannot be cancelled", "PERSONAL_TASK_CANCEL_NOT_ALLOWED", status.HTTP_409_CONFLICT)

    def _apply_personal_completion_timestamp(self, task: Task, next_status: str | None) -> None:
        if next_status == TASK_STATUS_COMPLETED and task.completed_at is None:
            task.completed_at = datetime.now(timezone.utc)
        elif next_status == TASK_STATUS_ACTIVE:
            task.completed_at = None

    async def _build_task_list_item(
        self,
        task: Task,
        membership: ClassMembership | None,
        user_id: int,
    ) -> TaskListItem:
        progress = None
        if task.visibility == TASK_VISIBILITY_SHARED and membership is not None:
            progress = await self.progress_repository.get_by_task_and_membership(task.id, membership.id)

        return TaskListItem(
            id=task.id,
            classroom_id=task.classroom_id,
            class_course_id=task.class_course_id,
            created_by_user_id=task.created_by_user_id,
            title=task.title,
            description=task.description,
            task_type=task.task_type,
            visibility=task.visibility,
            priority=task.priority,
            status=task.status,
            deadline=task.deadline,
            completed_at=task.completed_at,
            created_at=task.created_at,
            updated_at=task.updated_at,
            creator=TaskCreatorRead.model_validate(task.creator),
            course=self._build_course_read(task),
            my_progress=self._build_progress_read(task, progress),
            can_manage=self._can_manage_task(task, membership, user_id),
        )

    async def _build_task_read(
        self,
        task: Task,
        membership: ClassMembership | None,
        user_id: int,
        include_attachments: bool = False,
    ) -> TaskRead:
        item = await self._build_task_list_item(task, membership, user_id)
        return TaskRead(
            **item.model_dump(),
            attachments=[
                TaskAttachmentRead.model_validate(attachment)
                for attachment in task.attachments
            ] if include_attachments else [],
        )

    def _build_course_read(self, task: Task) -> TaskCourseRead | None:
        if task.class_course is None or task.class_course.course is None:
            return None

        return TaskCourseRead.model_validate(task.class_course.course)

    def _build_progress_read(self, task: Task, progress: TaskProgress | None) -> TaskProgressRead:
        if task.visibility == TASK_VISIBILITY_PERSONAL:
            if task.status == TASK_STATUS_COMPLETED:
                return TaskProgressRead(status=TASK_PROGRESS_COMPLETED, completed_at=task.completed_at)
            return TaskProgressRead(status=TASK_PROGRESS_PENDING, completed_at=None)

        if progress is None:
            return TaskProgressRead(status=TASK_PROGRESS_PENDING, completed_at=None)

        return TaskProgressRead(status=progress.status, completed_at=progress.completed_at)

    def _can_manage_task(self, task: Task, membership: ClassMembership | None, user_id: int) -> bool:
        if task.visibility == TASK_VISIBILITY_SHARED:
            return membership is not None and self._is_representative(membership)

        return task.created_by_user_id == user_id

    def _validate_attachment_name(self, file_name: str | None) -> tuple[str, str]:
        if not file_name:
            raise ClassFlowError("Attachment filename is required", "ATTACHMENT_FILENAME_REQUIRED", status.HTTP_422_UNPROCESSABLE_CONTENT)

        safe_name = Path(file_name).name
        extension = Path(safe_name).suffix.lower().lstrip(".")

        if not safe_name or safe_name in {".", ".."}:
            raise ClassFlowError("Invalid attachment filename", "INVALID_ATTACHMENT_FILENAME", status.HTTP_422_UNPROCESSABLE_CONTENT)

        if extension not in settings.TASK_ATTACHMENT_ALLOWED_EXTENSIONS:
            raise ClassFlowError("Attachment file type is not allowed", "ATTACHMENT_EXTENSION_NOT_ALLOWED", status.HTTP_422_UNPROCESSABLE_CONTENT)

        return safe_name, extension

    def _validate_attachment_content_type(self, content_type: str | None) -> str:
        if content_type not in settings.TASK_ATTACHMENT_ALLOWED_CONTENT_TYPES:
            raise ClassFlowError("Attachment content type is not allowed", "ATTACHMENT_CONTENT_TYPE_NOT_ALLOWED", status.HTTP_422_UNPROCESSABLE_CONTENT)

        return content_type

    async def _read_validated_attachment_bytes(self, file: UploadFile) -> bytes:
        max_size = settings.TASK_ATTACHMENT_MAX_SIZE_BYTES
        file_bytes = await file.read(max_size + 1)

        if len(file_bytes) > max_size:
            raise ClassFlowError("Attachment file is too large", "ATTACHMENT_TOO_LARGE", status.HTTP_413_CONTENT_TOO_LARGE)

        if len(file_bytes) == 0:
            raise ClassFlowError("Attachment file is empty", "ATTACHMENT_EMPTY", status.HTTP_422_UNPROCESSABLE_CONTENT)

        return file_bytes

    def _storage_root(self) -> Path:
        storage_root = Path(settings.TASK_ATTACHMENT_STORAGE_DIR)
        if not storage_root.is_absolute():
            storage_root = Path.cwd() / storage_root
        return storage_root.resolve()

    def _attachment_path(self, storage_key: str) -> Path:
        storage_root = self._storage_root()
        file_path = (storage_root / storage_key).resolve()

        # Storage keys are internal, but keep the path check so a bad DB value cannot escape storage/.
        if storage_root not in file_path.parents and file_path != storage_root:
            raise ClassFlowError("Invalid attachment storage key", "INVALID_ATTACHMENT_STORAGE_KEY", status.HTTP_500_INTERNAL_SERVER_ERROR)

        return file_path

    def _delete_file_if_present(self, file_path: Path) -> None:
        try:
            if file_path.exists() and file_path.is_file():
                file_path.unlink()
        except OSError:
            pass
