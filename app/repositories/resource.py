from sqlalchemy import select

from app.models.resource import RESOURCE_INDEX_PENDING, Resource
from app.repositories.base import BaseRepository
from app.repositories.content_access import accessible_class_content
from app.schemas.resource import ResourceCreate, ResourceUpdate


class ResourceRepository(BaseRepository[Resource]):
    async def create(
        self,
        classroom_id: int,
        uploaded_by_user_id: int,
        resource_in: ResourceCreate,
        file_name: str,
        storage_key: str,
        content_type: str,
        file_size: int,
        checksum_sha256: str,
    ) -> Resource:
        resource = Resource(
            classroom_id=classroom_id,
            uploaded_by_user_id=uploaded_by_user_id,
            **resource_in.model_dump(),
            file_name=file_name,
            storage_key=storage_key,
            content_type=content_type,
            file_size=file_size,
            checksum_sha256=checksum_sha256,
            indexing_status=RESOURCE_INDEX_PENDING,
        )
        self.session.add(resource)
        await self.session.flush()
        return resource

    async def get_by_id(self, resource_id: int, *, for_update: bool = False) -> Resource | None:
        statement = select(Resource).where(Resource.id == resource_id)
        if for_update:
            statement = statement.with_for_update().execution_options(populate_existing=True)
        return await self.session.scalar(statement)

    async def list_accessible_for_class(self, classroom_id: int, user_id: int) -> list[Resource]:
        result = await self.session.scalars(
            select(Resource)
            .where(
                Resource.classroom_id == classroom_id,
                Resource.is_enabled.is_(True),
                accessible_class_content(Resource, user_id),
            )
            .order_by(Resource.created_at.desc(), Resource.id.desc())
        )
        return list(result.all())

    async def update(self, resource: Resource, resource_in: ResourceUpdate) -> Resource:
        for field, value in resource_in.model_dump(exclude_unset=True).items():
            setattr(resource, field, value)
        await self.session.flush()
        return resource

    async def delete(self, resource: Resource) -> None:
        await self.session.delete(resource)
        await self.session.flush()
