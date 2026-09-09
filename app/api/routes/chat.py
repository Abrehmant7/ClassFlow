from typing import Annotated
from fastapi import APIRouter, Depends, File, Form, UploadFile
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.dependencies import get_approved_membership, get_current_user, require_representative
from app.core.config import settings
from app.database.session import get_db_session
from app.models.classroom import ClassMembership
from app.models.user import User
from app.schemas.chat import ChatRequest, ChatResponse, RagReindexResponse
from app.services.rag import RagChatService

router = APIRouter(tags=["chat"])


@router.post("/classes/{class_id}/chat", response_model=ChatResponse)
async def chat_with_class(
    class_id: int,
    request: ChatRequest,
    current_user: Annotated[User, Depends(get_current_user)],
    _membership: Annotated[ClassMembership, Depends(get_approved_membership)],
    session: Annotated[AsyncSession, Depends(get_db_session)],
) -> ChatResponse:
    service = RagChatService(session)
    return await service.answer_class_question(class_id, current_user.id, request.message)


@router.post("/classes/{class_id}/chat/file", response_model=ChatResponse)
async def chat_with_uploaded_file(
    class_id: int,
    message: Annotated[str, Form(min_length=1, max_length=2000)],
    file: Annotated[UploadFile, File()],
    current_user: Annotated[User, Depends(get_current_user)],
    _membership: Annotated[ClassMembership, Depends(get_approved_membership)],
    session: Annotated[AsyncSession, Depends(get_db_session)],
) -> ChatResponse:
    try:
        file_bytes = await file.read(settings.RAG_CHAT_FILE_MAX_SIZE_BYTES + 1)
    finally:
        await file.close()

    return await RagChatService(session).answer_class_question_with_file(
        classroom_id=class_id,
        user_id=current_user.id,
        question=message,
        file_name=file.filename or "",
        content_type=file.content_type,
        file_bytes=file_bytes,
    )


@router.post("/classes/{class_id}/chat/reindex", response_model=RagReindexResponse)
async def reindex_class_chat_sources(
    class_id: int,
    _membership: Annotated[ClassMembership, Depends(require_representative)],
    session: Annotated[AsyncSession, Depends(get_db_session)],
) -> RagReindexResponse:
    indexed_tasks, indexed_courses, indexed_attachments = await RagChatService(
        session
    ).reindex_class_sources(class_id)
    return RagReindexResponse(
        indexed_tasks=indexed_tasks,
        indexed_courses=indexed_courses,
        indexed_attachments=indexed_attachments,
    )
