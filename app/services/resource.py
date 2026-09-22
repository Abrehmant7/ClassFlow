from dataclasses import asdict

from fastapi import UploadFile, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import ClassFlowError
from app.models.classroom import CLASS_ROLE_REPRESENTATIVE, ClassMembership
from app.models.resource import RESOURCE_INDEX_PENDING, Resource
from app.repositories.resource import ResourceRepository
from app.schemas.resource import ResourceCreate, ResourceDownload, ResourceRead, ResourceUpdate
from app.services.content_access import ClassContentAccess
from app.services.rag import RagChatService
from app.services.resource_storage import remove_resource_file, resource_file_path, store_resource_pdf


class ResourceService:
    def __init__(
        self,
        session: AsyncSession,
        repository: ResourceRepository | None = None,
        access: ClassContentAccess | None = None,
        rag_service: RagChatService | None = None,
    ) -> None:
        self.session = session
        self.repository = repository or ResourceRepository(session)
        self.access = access or ClassContentAccess(session)
        self.rag_service = rag_service or RagChatService(session)

    async def upload_resource(self, classroom_id: int, resource_in: ResourceCreate, user_id: int, file: UploadFile) -> ResourceRead:
        stored = None
        persisted = False
        try:
            await self.access.require_representative(classroom_id, user_id)
            await self.access.validate_course(classroom_id, resource_in.class_course_id)
            stored = await store_resource_pdf(file)
            try:
                resource = await self.repository.create(
                    classroom_id=classroom_id,
                    uploaded_by_user_id=user_id,
                    resource_in=resource_in,
                    **asdict(stored),
                )
                await self.session.commit()
                persisted = True
            except Exception:
                await self.session.rollback()
                raise

            resource_id = resource.id
            # The file and pending row survive extraction/provider failures.
            await self.rag_service.index_resource(resource)
            return await self.get_resource(resource_id, user_id)
        finally:
            try:
                await file.close()
            finally:
                if stored is not None and not persisted:
                    remove_resource_file(resource_file_path(stored.storage_key))

    async def list_resources(self, classroom_id: int, user_id: int) -> list[ResourceRead]:
        membership = await self.access.approved_member(classroom_id, user_id)
        if membership is None:
            raise self._not_found()
        resources = await self.repository.list_accessible_for_class(classroom_id, user_id)
        return [self._read(resource, membership) for resource in resources]

    async def get_resource(self, resource_id: int, user_id: int) -> ResourceRead:
        resource, membership = await self._authorized_resource(resource_id, user_id)
        return self._read(resource, membership)

    async def get_resource_download(self, resource_id: int, user_id: int) -> ResourceDownload:
        resource, _membership = await self._authorized_resource(resource_id, user_id)
        path = resource_file_path(resource.storage_key)
        if not path.is_file():
            raise self._not_found()
        return ResourceDownload(file_path=str(path), file_name=resource.file_name, content_type=resource.content_type)

    async def update_resource(self, resource_id: int, resource_in: ResourceUpdate, user_id: int) -> ResourceRead:
        resource, membership = await self._authorized_resource(resource_id, user_id, manage=True, for_update=True)
        if not resource_in.model_fields_set:
            return self._read(resource, membership)
        resource = await self.repository.update(resource, resource_in)
        resource.indexing_status = RESOURCE_INDEX_PENDING
        resource.indexing_error = None
        resource.indexed_at = None
        await self.rag_service.delete_resource(resource_id)
        await self.session.commit()
        if resource.is_enabled:
            await self.rag_service.index_resource(resource)
        resource, membership = await self._authorized_resource(resource_id, user_id, manage=True)
        return self._read(resource, membership)

    async def reindex_resource(self, resource_id: int, user_id: int) -> ResourceRead:
        resource, _membership = await self._authorized_resource(resource_id, user_id, manage=True)
        if not resource.is_enabled:
            raise ClassFlowError("Enable the resource before indexing", "RESOURCE_DISABLED", status.HTTP_409_CONFLICT)
        await self.rag_service.index_resource(resource)
        return await self.get_resource(resource_id, user_id)

    async def delete_resource(self, resource_id: int, user_id: int) -> None:
        resource, _membership = await self._authorized_resource(resource_id, user_id, manage=True, for_update=True)
        path = resource_file_path(resource.storage_key)
        try:
            await self.rag_service.delete_resource(resource_id)
            await self.repository.delete(resource)
            await self.session.commit()
        except Exception:
            await self.session.rollback()
            raise
        remove_resource_file(path)

    async def _authorized_resource(
        self, resource_id: int, user_id: int, *, manage: bool = False, for_update: bool = False,
    ) -> tuple[Resource, ClassMembership]:
        resource = await self.repository.get_by_id(resource_id, for_update=for_update)
        if resource is None:
            raise self._not_found()
        membership = await self.access.can_read(resource.classroom_id, resource.class_course_id, user_id)
        if membership is None:
            raise self._not_found()
        if manage and membership.role != CLASS_ROLE_REPRESENTATIVE:
            raise ClassFlowError("Class representative access required", "CLASS_REPRESENTATIVE_REQUIRED", status.HTTP_403_FORBIDDEN)
        if not manage and not resource.is_enabled:
            raise self._not_found()
        return resource, membership

    @staticmethod
    def _read(resource: Resource, membership: ClassMembership) -> ResourceRead:
        return ResourceRead.model_validate({
            **{field: getattr(resource, field) for field in ResourceRead.model_fields if field != "can_manage"},
            "can_manage": membership.role == CLASS_ROLE_REPRESENTATIVE,
        })

    @staticmethod
    def _not_found() -> ClassFlowError:
        return ClassFlowError("Resource not found", "RESOURCE_NOT_FOUND", status.HTTP_404_NOT_FOUND)
