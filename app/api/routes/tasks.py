from typing import Annotated

from fastapi import APIRouter, Depends, File, Query, Response, UploadFile, status
from fastapi.responses import FileResponse
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.dependencies import get_approved_membership, get_current_user
from app.database.session import get_db_session
from app.models.classroom import ClassMembership
from app.models.user import User
from app.repositories.course import ClassCourseRepository, CourseRegistrationRepository
from app.repositories.membership import ClassMembershipRepository
from app.repositories.task import TaskAttachmentRepository, TaskProgressRepository, TaskRepository
from app.schemas.task import PersonalTaskCreate, TaskAttachmentRead, TaskCreate, TaskListItem, TaskProgressUpdate, TaskRead, TaskUpdate
from app.services.task import TaskService

router = APIRouter(tags=["tasks"])


def get_task_service(session: AsyncSession) -> TaskService:
    return TaskService(
        task_repository=TaskRepository(session),
        progress_repository=TaskProgressRepository(session),
        attachment_repository=TaskAttachmentRepository(session),
        membership_repository=ClassMembershipRepository(session),
        class_course_repository=ClassCourseRepository(session),
        registration_repository=CourseRegistrationRepository(session),
    )


@router.post("/classes/{class_id}/tasks", response_model=TaskRead, status_code=status.HTTP_201_CREATED)
async def create_task(
    class_id: int,
    task_in: TaskCreate,
    current_user: Annotated[User, Depends(get_current_user)],
    _membership: Annotated[ClassMembership, Depends(get_approved_membership)],
    session: Annotated[AsyncSession, Depends(get_db_session)],
) -> TaskRead:
    service = get_task_service(session)
    return await service.create_class_task(class_id, task_in, current_user.id)


@router.post("/tasks", response_model=TaskRead, status_code=status.HTTP_201_CREATED)
async def create_personal_task(
    task_in: TaskCreate,
    current_user: Annotated[User, Depends(get_current_user)],
    session: Annotated[AsyncSession, Depends(get_db_session)],
) -> TaskRead:
    service = get_task_service(session)
    return await service.create_personal_task(task_in, current_user.id)


@router.post("/personal-tasks", response_model=TaskRead, status_code=status.HTTP_201_CREATED)
async def create_personal_task_from_feed(
    task_in: PersonalTaskCreate,
    current_user: Annotated[User, Depends(get_current_user)],
    session: Annotated[AsyncSession, Depends(get_db_session)],
) -> TaskRead:
    service = get_task_service(session)
    return await service.create_personal_task(task_in.to_task_create(), current_user.id)


@router.get("/classes/{class_id}/tasks", response_model=list[TaskListItem])
async def list_tasks(
    class_id: int,
    current_user: Annotated[User, Depends(get_current_user)],
    _membership: Annotated[ClassMembership, Depends(get_approved_membership)],
    session: Annotated[AsyncSession, Depends(get_db_session)],
    include_closed: bool = Query(default=False),
) -> list[TaskListItem]:
    service = get_task_service(session)
    return await service.list_tasks(class_id, current_user.id, include_closed)


@router.get("/tasks", response_model=list[TaskListItem])
async def list_feed_tasks(
    current_user: Annotated[User, Depends(get_current_user)],
    session: Annotated[AsyncSession, Depends(get_db_session)],
    include_closed: bool = Query(default=False),
) -> list[TaskListItem]:
    service = get_task_service(session)
    return await service.list_feed_tasks(current_user.id, include_closed)


@router.get("/tasks/{task_id}", response_model=TaskRead)
async def read_task(
    task_id: int,
    current_user: Annotated[User, Depends(get_current_user)],
    session: Annotated[AsyncSession, Depends(get_db_session)],
) -> TaskRead:
    service = get_task_service(session)
    return await service.get_task(task_id, current_user.id)


@router.patch("/tasks/{task_id}", response_model=TaskRead)
async def update_task(
    task_id: int,
    task_in: TaskUpdate,
    current_user: Annotated[User, Depends(get_current_user)],
    session: Annotated[AsyncSession, Depends(get_db_session)],
) -> TaskRead:
    service = get_task_service(session)
    return await service.update_task(task_id, task_in, current_user.id)


@router.delete("/tasks/{task_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_task(
    task_id: int,
    current_user: Annotated[User, Depends(get_current_user)],
    session: Annotated[AsyncSession, Depends(get_db_session)],
) -> Response:
    service = get_task_service(session)
    await service.delete_task(task_id, current_user.id)
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.put("/tasks/{task_id}/progress", response_model=TaskRead)
async def update_task_progress(
    task_id: int,
    progress_in: TaskProgressUpdate,
    current_user: Annotated[User, Depends(get_current_user)],
    session: Annotated[AsyncSession, Depends(get_db_session)],
) -> TaskRead:
    service = get_task_service(session)
    return await service.update_progress(task_id, progress_in, current_user.id)


@router.put("/personal-tasks/{task_id}/complete", response_model=TaskRead)
async def complete_personal_task(
    task_id: int,
    current_user: Annotated[User, Depends(get_current_user)],
    session: Annotated[AsyncSession, Depends(get_db_session)],
) -> TaskRead:
    service = get_task_service(session)
    return await service.complete_personal_task(task_id, current_user.id)


@router.put("/personal-tasks/{task_id}/reopen", response_model=TaskRead)
async def reopen_personal_task(
    task_id: int,
    current_user: Annotated[User, Depends(get_current_user)],
    session: Annotated[AsyncSession, Depends(get_db_session)],
) -> TaskRead:
    service = get_task_service(session)
    return await service.reopen_personal_task(task_id, current_user.id)


@router.post("/tasks/{task_id}/attachments", response_model=TaskAttachmentRead, status_code=status.HTTP_201_CREATED)
async def upload_task_attachment(
    task_id: int,
    current_user: Annotated[User, Depends(get_current_user)],
    session: Annotated[AsyncSession, Depends(get_db_session)],
    file: UploadFile = File(...),
) -> TaskAttachmentRead:
    service = get_task_service(session)
    return await service.upload_attachment(task_id, current_user.id, file)


@router.get("/tasks/{task_id}/attachments", response_model=list[TaskAttachmentRead])
async def list_task_attachments(
    task_id: int,
    current_user: Annotated[User, Depends(get_current_user)],
    session: Annotated[AsyncSession, Depends(get_db_session)],
) -> list[TaskAttachmentRead]:
    service = get_task_service(session)
    return await service.list_attachments(task_id, current_user.id)


@router.get("/attachments/{attachment_id}/download")
async def download_task_attachment(
    attachment_id: int,
    current_user: Annotated[User, Depends(get_current_user)],
    session: Annotated[AsyncSession, Depends(get_db_session)],
) -> FileResponse:
    service = get_task_service(session)
    download = await service.get_attachment_download(attachment_id, current_user.id)
    return FileResponse(
        path=download.file_path,
        filename=download.file_name,
        media_type=download.file_type,
    )


@router.delete("/attachments/{attachment_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_task_attachment(
    attachment_id: int,
    current_user: Annotated[User, Depends(get_current_user)],
    session: Annotated[AsyncSession, Depends(get_db_session)],
) -> Response:
    service = get_task_service(session)
    await service.delete_attachment(attachment_id, current_user.id)
    return Response(status_code=status.HTTP_204_NO_CONTENT)
