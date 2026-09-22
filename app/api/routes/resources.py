from typing import Annotated

from fastapi import APIRouter, Depends, File, Form, Response, UploadFile, status
from fastapi.responses import FileResponse
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.dependencies import get_current_user
from app.database.session import get_db_session
from app.models.user import User
from app.schemas.resource import ResourceCreate, ResourceRead, ResourceTitle, ResourceUpdate
from app.services.resource import ResourceService

router = APIRouter(tags=["resources"])


@router.post("/classes/{class_id}/resources", response_model=ResourceRead, status_code=status.HTTP_201_CREATED)
async def upload_resource(
    class_id: int,
    current_user: Annotated[User, Depends(get_current_user)],
    session: Annotated[AsyncSession, Depends(get_db_session)],
    title: Annotated[ResourceTitle, Form()],
    file: Annotated[UploadFile, File()],
    description: Annotated[str | None, Form()] = None,
    class_course_id: Annotated[int | None, Form(ge=1)] = None,
) -> ResourceRead:
    resource_in = ResourceCreate(title=title, description=description, class_course_id=class_course_id)
    return await ResourceService(session).upload_resource(class_id, resource_in, current_user.id, file)


@router.get("/classes/{class_id}/resources", response_model=list[ResourceRead])
async def list_resources(
    class_id: int,
    current_user: Annotated[User, Depends(get_current_user)],
    session: Annotated[AsyncSession, Depends(get_db_session)],
) -> list[ResourceRead]:
    return await ResourceService(session).list_resources(class_id, current_user.id)


@router.get("/resources/{resource_id}", response_model=ResourceRead)
async def read_resource(
    resource_id: int,
    current_user: Annotated[User, Depends(get_current_user)],
    session: Annotated[AsyncSession, Depends(get_db_session)],
) -> ResourceRead:
    return await ResourceService(session).get_resource(resource_id, current_user.id)


@router.get("/resources/{resource_id}/download")
async def download_resource(
    resource_id: int,
    current_user: Annotated[User, Depends(get_current_user)],
    session: Annotated[AsyncSession, Depends(get_db_session)],
) -> FileResponse:
    download = await ResourceService(session).get_resource_download(resource_id, current_user.id)
    return FileResponse(
        path=download.file_path,
        filename=download.file_name,
        media_type=download.content_type,
        headers={"Cache-Control": "private, no-store", "X-Content-Type-Options": "nosniff"},
    )


@router.patch("/resources/{resource_id}", response_model=ResourceRead)
async def update_resource(
    resource_id: int,
    resource_in: ResourceUpdate,
    current_user: Annotated[User, Depends(get_current_user)],
    session: Annotated[AsyncSession, Depends(get_db_session)],
) -> ResourceRead:
    return await ResourceService(session).update_resource(resource_id, resource_in, current_user.id)


@router.delete("/resources/{resource_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_resource(
    resource_id: int,
    current_user: Annotated[User, Depends(get_current_user)],
    session: Annotated[AsyncSession, Depends(get_db_session)],
) -> Response:
    await ResourceService(session).delete_resource(resource_id, current_user.id)
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.post("/resources/{resource_id}/reindex", response_model=ResourceRead)
async def reindex_resource(
    resource_id: int,
    current_user: Annotated[User, Depends(get_current_user)],
    session: Annotated[AsyncSession, Depends(get_db_session)],
) -> ResourceRead:
    return await ResourceService(session).reindex_resource(resource_id, current_user.id)

