from datetime import datetime, timezone
from io import BytesIO
from pathlib import Path
import shutil
from uuid import uuid4

import pytest
from fastapi import UploadFile
from starlette.datastructures import Headers

from app.core.exceptions import ClassFlowError
from app.models.classroom import CLASS_ROLE_REPRESENTATIVE, CLASS_ROLE_STUDENT, MEMBERSHIP_STATUS_APPROVED, ClassMembership
from app.models.course import ClassCourse
from app.models.task import (
    TASK_PROGRESS_COMPLETED,
    TASK_PROGRESS_PENDING,
    TASK_STATUS_ACTIVE,
    TASK_STATUS_CANCELLED,
    TASK_STATUS_COMPLETED,
    TASK_VISIBILITY_PERSONAL,
    TASK_VISIBILITY_SHARED,
    Task,
    TaskAttachment,
    TaskProgress,
)
from app.models.user import User
from app.schemas.task import TaskCreate, TaskProgressUpdate, TaskUpdate
from app.services.task import TaskService


class FakeSession:
    async def commit(self) -> None:
        return None

    async def rollback(self) -> None:
        return None


class FakeTaskRepository:
    def __init__(self, tasks: dict[int, Task] | None = None) -> None:
        self.session = FakeSession()
        self.tasks = tasks or {}
        self.next_id = max(self.tasks, default=0) + 1

    async def create(self, classroom_id: int | None, task_in: TaskCreate, created_by_user_id: int) -> Task:
        task = make_task(
            task_id=self.next_id,
            classroom_id=classroom_id,
            created_by_user_id=created_by_user_id,
            visibility=task_in.visibility,
            class_course_id=task_in.class_course_id,
        )
        task.title = task_in.title
        task.description = task_in.description
        task.task_type = task_in.task_type
        task.priority = task_in.priority
        task.deadline = task_in.deadline
        self.tasks[task.id] = task
        self.next_id += 1
        return task

    async def get_by_id(self, task_id: int) -> Task | None:
        return self.tasks.get(task_id)

    async def update(self, task: Task, task_in: TaskUpdate) -> Task:
        update_data = task_in.model_dump(exclude_unset=True)

        for field, value in update_data.items():
            setattr(task, field, value)

        return task

    async def list_feed_for_user(self, user_id: int, include_closed: bool = False) -> list[Task]:
        return [
            task
            for task in self.tasks.values()
            if task.visibility == TASK_VISIBILITY_PERSONAL and task.created_by_user_id == user_id
        ]

    async def delete(self, task: Task) -> None:
        self.tasks.pop(task.id, None)


class FakeProgressRepository:
    def __init__(self) -> None:
        self.rows: dict[tuple[int, int], TaskProgress] = {}

    async def get_by_task_and_membership(self, task_id: int, membership_id: int) -> TaskProgress | None:
        return self.rows.get((task_id, membership_id))

    async def upsert_for_membership(
        self,
        task_id: int,
        membership_id: int,
        progress_status: str,
        completed_at: datetime | None,
    ) -> TaskProgress:
        key = (task_id, membership_id)
        progress = self.rows.get(key)

        if progress is None:
            progress = TaskProgress(
                id=len(self.rows) + 1,
                task_id=task_id,
                membership_id=membership_id,
                status=progress_status,
                completed_at=completed_at,
            )
            self.rows[key] = progress
        else:
            progress.status = progress_status
            progress.completed_at = completed_at

        return progress


class FakeAttachmentRepository:
    def __init__(self, attachments: dict[int, TaskAttachment] | None = None) -> None:
        self.attachments = attachments or {}
        self.next_id = max(self.attachments, default=0) + 1

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
            id=self.next_id,
            task_id=task_id,
            uploaded_by_user_id=uploaded_by_user_id,
            file_name=file_name,
            storage_key=storage_key,
            file_type=file_type,
            file_size=file_size,
        )
        self.attachments[attachment.id] = attachment
        self.next_id += 1
        return attachment

    async def get_by_id(self, attachment_id: int) -> TaskAttachment | None:
        return self.attachments.get(attachment_id)

    async def list_for_task(self, task_id: int) -> list[TaskAttachment]:
        return [attachment for attachment in self.attachments.values() if attachment.task_id == task_id]

    async def delete(self, attachment: TaskAttachment) -> None:
        self.attachments.pop(attachment.id, None)


class FakeMembershipRepository:
    def __init__(self, memberships: list[ClassMembership]) -> None:
        self.memberships = {
            (membership.user_id, membership.classroom_id): membership
            for membership in memberships
        }

    async def get_by_user_and_class(self, user_id: int, classroom_id: int) -> ClassMembership | None:
        return self.memberships.get((user_id, classroom_id))


class FakeClassCourseRepository:
    def __init__(self, class_courses: dict[int, ClassCourse]) -> None:
        self.class_courses = class_courses

    async def get_by_id(self, class_course_id: int) -> ClassCourse | None:
        return self.class_courses.get(class_course_id)


class FakeRegistrationRepository:
    def __init__(self, active_registration_keys: set[tuple[int, int]] | None = None) -> None:
        self.active_registration_keys = active_registration_keys or set()

    async def get_by_membership_and_class_course(self, membership_id: int, class_course_id: int):
        if (membership_id, class_course_id) not in self.active_registration_keys:
            return None

        return object_with_attrs(is_active=True)


def object_with_attrs(**attrs):
    return type("ObjectWithAttrs", (), attrs)()


def make_membership(
    membership_id: int,
    user_id: int,
    classroom_id: int,
    role: str = CLASS_ROLE_STUDENT,
) -> ClassMembership:
    return ClassMembership(
        id=membership_id,
        user_id=user_id,
        classroom_id=classroom_id,
        role=role,
        status=MEMBERSHIP_STATUS_APPROVED,
    )


def make_class_course(class_course_id: int, classroom_id: int, is_active: bool = True) -> ClassCourse:
    return ClassCourse(
        id=class_course_id,
        classroom_id=classroom_id,
        course_id=class_course_id,
        is_active=is_active,
        is_default=False,
        created_by_user_id=1,
    )


def make_task(
    task_id: int,
    classroom_id: int | None,
    created_by_user_id: int,
    visibility: str = TASK_VISIBILITY_SHARED,
    class_course_id: int | None = None,
    status: str = TASK_STATUS_ACTIVE,
) -> Task:
    now = datetime.now(timezone.utc)
    return Task(
        id=task_id,
        classroom_id=classroom_id,
        class_course_id=class_course_id,
        created_by_user_id=created_by_user_id,
        title="Task",
        description=None,
        task_type="assignment",
        visibility=visibility,
        priority="medium",
        status=status,
        deadline=None,
        completed_at=None,
        created_at=now,
        updated_at=now,
        creator=User(id=created_by_user_id, username=f"user-{created_by_user_id}"),
        attachments=[],
    )


def make_upload(filename: str, content_type: str, content: bytes) -> UploadFile:
    return UploadFile(
        filename=filename,
        file=BytesIO(content),
        headers=Headers({"content-type": content_type}),
    )


@pytest.fixture
def attachment_storage_dir(monkeypatch: pytest.MonkeyPatch):
    storage_root = Path.cwd() / ".pytest_cache" / "task_attachment_storage" / uuid4().hex
    monkeypatch.setattr("app.services.task.settings.TASK_ATTACHMENT_STORAGE_DIR", str(storage_root))

    yield storage_root

    resolved_root = storage_root.resolve()
    allowed_root = (Path.cwd() / ".pytest_cache" / "task_attachment_storage").resolve()
    if resolved_root == allowed_root or allowed_root in resolved_root.parents:
        shutil.rmtree(resolved_root, ignore_errors=True)


def make_service(
    *,
    memberships: list[ClassMembership],
    tasks: dict[int, Task] | None = None,
    class_courses: dict[int, ClassCourse] | None = None,
    active_registration_keys: set[tuple[int, int]] | None = None,
    progress_repository: FakeProgressRepository | None = None,
    attachment_repository: FakeAttachmentRepository | None = None,
) -> TaskService:
    return TaskService(
        task_repository=FakeTaskRepository(tasks),
        progress_repository=progress_repository or FakeProgressRepository(),
        attachment_repository=attachment_repository or FakeAttachmentRepository(),
        membership_repository=FakeMembershipRepository(memberships),
        class_course_repository=FakeClassCourseRepository(class_courses or {}),
        registration_repository=FakeRegistrationRepository(active_registration_keys),
    )


@pytest.mark.anyio
async def test_cross_class_course_ids_are_rejected_for_shared_task_creation() -> None:
    representative = make_membership(1, user_id=10, classroom_id=1, role=CLASS_ROLE_REPRESENTATIVE)
    service = make_service(
        memberships=[representative],
        class_courses={7: make_class_course(7, classroom_id=2)},
    )

    with pytest.raises(ClassFlowError) as exc_info:
        await service.create_class_task(
            classroom_id=1,
            task_in=TaskCreate(
                title="Database Assignment",
                visibility="shared",
                class_course_id=7,
            ),
            user_id=10,
        )

    assert exc_info.value.detail["error_code"] == "CLASS_COURSE_NOT_FOUND"


@pytest.mark.anyio
async def test_inactive_courses_cannot_be_assigned_to_tasks() -> None:
    representative = make_membership(1, user_id=10, classroom_id=1, role=CLASS_ROLE_REPRESENTATIVE)
    service = make_service(
        memberships=[representative],
        class_courses={7: make_class_course(7, classroom_id=1, is_active=False)},
    )

    with pytest.raises(ClassFlowError) as exc_info:
        await service.create_class_task(
            classroom_id=1,
            task_in=TaskCreate(
                title="Database Assignment",
                visibility="shared",
                class_course_id=7,
            ),
            user_id=10,
        )

    assert exc_info.value.detail["error_code"] == "CLASS_COURSE_INACTIVE"


@pytest.mark.anyio
async def test_personal_task_can_be_created_without_classroom() -> None:
    service = make_service(memberships=[])

    task = await service.create_personal_task(
        task_in=TaskCreate(
            title="Prepare for internship interview",
            visibility=TASK_VISIBILITY_PERSONAL,
        ),
        user_id=20,
    )

    assert task.visibility == TASK_VISIBILITY_PERSONAL
    assert task.classroom_id is None
    assert task.class_course_id is None
    assert task.can_manage is True


@pytest.mark.anyio
async def test_personal_task_completion_does_not_delete_task() -> None:
    task = make_task(
        1,
        classroom_id=None,
        created_by_user_id=20,
        visibility=TASK_VISIBILITY_PERSONAL,
    )
    service = make_service(memberships=[], tasks={task.id: task})

    updated = await service.update_task(
        task.id,
        TaskUpdate(status=TASK_STATUS_COMPLETED),
        user_id=20,
    )

    assert updated.status == TASK_STATUS_COMPLETED
    assert updated.completed_at is not None
    assert task.id in service.task_repository.tasks


@pytest.mark.anyio
async def test_personal_task_remains_invisible_to_class_representative() -> None:
    representative = make_membership(1, user_id=10, classroom_id=1, role=CLASS_ROLE_REPRESENTATIVE)
    task = make_task(
        1,
        classroom_id=1,
        created_by_user_id=20,
        visibility=TASK_VISIBILITY_PERSONAL,
    )
    service = make_service(memberships=[representative], tasks={task.id: task})

    with pytest.raises(ClassFlowError) as exc_info:
        await service.get_task(task.id, user_id=10)

    assert exc_info.value.detail["error_code"] == "TASK_NOT_FOUND"


@pytest.mark.anyio
async def test_progress_updates_reuse_one_record_per_task_and_membership() -> None:
    student = make_membership(2, user_id=20, classroom_id=1)
    task = make_task(1, classroom_id=1, created_by_user_id=10)
    progress_repository = FakeProgressRepository()
    service = make_service(
        memberships=[student],
        tasks={task.id: task},
        progress_repository=progress_repository,
    )

    await service.update_progress(task.id, TaskProgressUpdate(status=TASK_PROGRESS_COMPLETED), user_id=20)
    await service.update_progress(task.id, TaskProgressUpdate(status=TASK_PROGRESS_PENDING), user_id=20)

    assert len(progress_repository.rows) == 1
    progress = progress_repository.rows[(task.id, student.id)]
    assert progress.status == TASK_PROGRESS_PENDING
    assert progress.completed_at is None


@pytest.mark.anyio
async def test_cancelled_tasks_cannot_be_completed() -> None:
    student = make_membership(2, user_id=20, classroom_id=1)
    task = make_task(1, classroom_id=1, created_by_user_id=10, status=TASK_STATUS_CANCELLED)
    service = make_service(memberships=[student], tasks={task.id: task})

    with pytest.raises(ClassFlowError) as exc_info:
        await service.update_progress(task.id, TaskProgressUpdate(status=TASK_PROGRESS_COMPLETED), user_id=20)

    assert exc_info.value.detail["error_code"] == "TASK_CLOSED_FOR_PROGRESS"


@pytest.mark.anyio
async def test_invalid_attachment_files_are_rejected() -> None:
    representative = make_membership(1, user_id=10, classroom_id=1, role=CLASS_ROLE_REPRESENTATIVE)
    task = make_task(1, classroom_id=1, created_by_user_id=10)
    service = make_service(memberships=[representative], tasks={task.id: task})
    upload = make_upload("malware.exe", "application/octet-stream", b"not really a document")

    with pytest.raises(ClassFlowError) as exc_info:
        await service.upload_attachment(task.id, user_id=10, file=upload)

    assert exc_info.value.detail["error_code"] == "ATTACHMENT_EXTENSION_NOT_ALLOWED"


@pytest.mark.anyio
async def test_oversized_attachment_files_are_rejected(
    monkeypatch: pytest.MonkeyPatch,
    attachment_storage_dir: Path,
) -> None:
    representative = make_membership(1, user_id=10, classroom_id=1, role=CLASS_ROLE_REPRESENTATIVE)
    task = make_task(1, classroom_id=1, created_by_user_id=10)
    service = make_service(memberships=[representative], tasks={task.id: task})
    monkeypatch.setattr("app.services.task.settings.TASK_ATTACHMENT_MAX_SIZE_BYTES", 4)
    upload = make_upload("notes.pdf", "application/pdf", b"12345")

    with pytest.raises(ClassFlowError) as exc_info:
        await service.upload_attachment(task.id, user_id=10, file=upload)

    assert exc_info.value.detail["error_code"] == "ATTACHMENT_TOO_LARGE"
    assert list(attachment_storage_dir.rglob("*")) == []


@pytest.mark.anyio
async def test_attachment_download_cannot_bypass_task_permissions() -> None:
    owner = make_membership(1, user_id=10, classroom_id=1, role=CLASS_ROLE_REPRESENTATIVE)
    unauthorized_student = make_membership(2, user_id=20, classroom_id=1)
    task = make_task(
        1,
        classroom_id=1,
        created_by_user_id=10,
        class_course_id=7,
    )
    attachment = TaskAttachment(
        id=1,
        task_id=task.id,
        uploaded_by_user_id=10,
        file_name="file.pdf",
        storage_key="tasks/1/file.pdf",
        file_type="application/pdf",
        file_size=3,
        task=task,
    )
    service = make_service(
        memberships=[owner, unauthorized_student],
        tasks={task.id: task},
        class_courses={7: make_class_course(7, classroom_id=1)},
        attachment_repository=FakeAttachmentRepository({attachment.id: attachment}),
    )

    with pytest.raises(ClassFlowError) as exc_info:
        await service.get_attachment_download(attachment.id, user_id=20)

    assert exc_info.value.detail["error_code"] == "COURSE_REGISTRATION_REQUIRED"
