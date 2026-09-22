"""Opt-in PostgreSQL checks: set CLASSFLOW_TEST_DATABASE_URL to a migrated database.

Each test runs inside an outer transaction. Service commits release savepoints;
the fixture rolls back all test rows. Embeddings never call an external provider.
"""
from hashlib import sha256
import os
from pathlib import Path

import httpx
import pytest
from sqlalchemy import delete, func, select

from app.core.config import settings
from app.core.exceptions import ClassFlowError
from app.core.security import create_access_token
from app.database.session import get_db_session
from app.main import create_app
from app.models.announcement import Announcement
from app.models.classroom import Classroom
from app.models.course import ClassCourse, CourseRegistration
from app.models.resource import RAG_SOURCE_RESOURCE, RagChunk, Resource
from app.repositories.announcement import AnnouncementRepository
from app.repositories.resource import ResourceRepository
from app.schemas.announcement import AnnouncementCreate, AnnouncementUpdate
from app.schemas.resource import ResourceCreate, ResourceUpdate
from app.services.content_access import ClassContentAccess
from tests.test_resource_storage import make_upload

pytestmark = [
    pytest.mark.anyio,
    pytest.mark.skipif(not os.getenv("CLASSFLOW_TEST_DATABASE_URL"), reason="Set CLASSFLOW_TEST_DATABASE_URL for PostgreSQL integration checks"),
]


@pytest.fixture
def anyio_backend():
    return "asyncio"




async def upload(env, *, course=False, title="Course notes"):
    return await env.service.upload_resource(
        env.classroom_id,
        ResourceCreate(title=title, description="A useful PDF", class_course_id=env.course_id if course else None),
        env.users["rep"],
        make_upload(content=env.pdf),
    )


async def resource_chunks(env, resource_id):
    return list((await env.session.scalars(select(RagChunk).where(
        RagChunk.source_type == RAG_SOURCE_RESOURCE, RagChunk.source_id == resource_id,
    ))).all())


async def test_upload_indexes_pdf_and_returns_only_public_metadata(env):
    result = await upload(env, course=True)
    assert result.indexing_status == "indexed"
    assert result.indexing_error is None
    assert result.indexed_at is not None
    assert result.file_size == len(env.pdf)
    assert result.can_manage is True
    assert not {"file_path", "storage_key", "checksum_sha256"} & result.model_dump().keys()
    record = await env.session.get(Resource, result.id)
    assert record.checksum_sha256 == sha256(env.pdf).hexdigest()
    assert (env.root / record.storage_key).read_bytes() == env.pdf
    chunks = await resource_chunks(env, result.id)
    assert len(chunks) == 1
    assert chunks[0].page_number == 1
    assert chunks[0].class_course_id == env.course_id
    assert chunks[0].source_title == "Course notes"


async def test_provider_failure_keeps_download_and_retry_replaces_chunks(env):
    env.ai.failure = RuntimeError("secret-key /private/server/provider-details")
    result = await upload(env)
    assert result.indexing_status == "failed"
    assert result.indexed_at is None
    assert "secret-key" not in result.indexing_error
    assert "/private/" not in result.indexing_error
    assert await resource_chunks(env, result.id) == []
    download = await env.service.get_resource_download(result.id, env.users["student"])
    assert Path(download.file_path).read_bytes() == env.pdf
    env.ai.failure = None
    retry = await env.service.reindex_resource(result.id, env.users["rep"])
    assert retry.indexing_status == "indexed"
    assert retry.indexing_error is None
    await env.service.reindex_resource(result.id, env.users["rep"])
    assert len(await resource_chunks(env, result.id)) == 1


async def test_failed_retry_clears_old_chunks_and_keeps_file(env):
    result = await upload(env)
    env.ai.failure = RuntimeError("unavailable")
    result = await env.service.reindex_resource(result.id, env.users["rep"])
    assert result.indexing_status == "failed"
    assert await resource_chunks(env, result.id) == []
    assert (await env.service.get_resource_download(result.id, env.users["student"])).file_name == "notes.pdf"


async def test_retrieval_excludes_resources_until_indexing_succeeds(env):
    result = await upload(env, course=True)
    matches = await env.rag.repository.search_accessible(env.classroom_id, env.users["student"], [0.1] * 768, 5, 0.8)
    assert [match.chunk.source_id for match in matches] == [result.id]
    resource = await env.session.get(Resource, result.id)
    for indexing_status in ("pending", "processing", "failed"):
        resource.indexing_status = indexing_status
        await env.session.commit()
        assert await env.rag.repository.search_accessible(env.classroom_id, env.users["student"], [0.1] * 768, 5, 0.8) == []


async def test_extraction_failure_keeps_uploaded_pdf(env):
    result = await env.service.upload_resource(
        env.classroom_id, ResourceCreate(title="Broken PDF"), env.users["rep"],
        make_upload(content=b"%PDF-1.7\nmalformed PDF"),
    )
    assert result.indexing_status == "failed"
    assert "PDF could not be read" in result.indexing_error
    assert (await env.service.get_resource_download(result.id, env.users["student"])).file_name == "notes.pdf"


@pytest.mark.parametrize("role,expected", [
    ("rep", {"class", "course"}), ("student", {"class", "course"}),
    ("unregistered", {"class"}), ("pending", set()), ("removed", set()), ("outsider", set()),
])
async def test_resource_and_announcement_audiences_are_enforced_by_sql_and_service(env, role, expected):
    resources = {"class": await upload(env, title="class"), "course": await upload(env, course=True, title="course")}
    announcements = AnnouncementRepository(env.session)
    for scope in resources:
        await announcements.create(env.classroom_id, env.users["rep"], AnnouncementCreate(
            title=scope, body="Announcement body", class_course_id=env.course_id if scope == "course" else None,
        ))
    await env.session.commit()
    user_id = env.users[role]
    listed = await ResourceRepository(env.session).list_accessible_for_class(env.classroom_id, user_id)
    assert {resource.title for resource in listed} == expected
    listed_announcements = await announcements.list_accessible_for_class(env.classroom_id, user_id)
    assert {announcement.title for announcement in listed_announcements} == expected
    for scope, resource in resources.items():
        if scope in expected:
            assert (await env.service.get_resource(resource.id, user_id)).can_manage == (role == "rep")
            assert Path((await env.service.get_resource_download(resource.id, user_id)).file_path).is_file()
        else:
            for operation in (env.service.get_resource, env.service.get_resource_download):
                with pytest.raises(ClassFlowError) as caught:
                    await operation(resource.id, user_id)
                assert caught.value.status_code == 404


@pytest.mark.parametrize("role", ["student", "unregistered", "pending", "removed", "outsider"])
async def test_upload_requires_representative_before_writing_files(env, role):
    file = make_upload(content=env.pdf)
    with pytest.raises(ClassFlowError) as caught:
        await env.service.upload_resource(env.classroom_id, ResourceCreate(title="Not allowed"), env.users[role], file)
    assert caught.value.status_code == 403
    assert file.file.closed
    assert list(env.root.glob("*")) == []


async def test_cross_class_course_and_inactive_course_are_rejected_before_upload(env):
    for course_id in (env.other_course_id, env.course_id):
        if course_id == env.course_id:
            course = await env.session.get(ClassCourse, course_id)
            course.is_active = False
            await env.session.commit()
        with pytest.raises(ClassFlowError) as caught:
            await env.service.upload_resource(env.classroom_id, ResourceCreate(title="Wrong course", class_course_id=course_id), env.users["rep"], make_upload(content=env.pdf))
        assert caught.value.status_code == 404
    assert list(env.root.glob("*")) == []


async def test_inactive_classroom_and_dropped_registration_hide_content(env):
    result = await upload(env, course=True)
    registration = await env.session.scalar(select(CourseRegistration).where(CourseRegistration.class_course_id == env.course_id))
    registration.is_active = False
    await env.session.commit()
    assert await ResourceRepository(env.session).list_accessible_for_class(env.classroom_id, env.users["student"]) == []
    with pytest.raises(ClassFlowError):
        await env.service.get_resource_download(result.id, env.users["student"])
    classroom = await env.session.get(Classroom, env.classroom_id)
    classroom.is_active = False
    await env.session.commit()
    assert await ResourceRepository(env.session).list_accessible_for_class(env.classroom_id, env.users["rep"]) == []
    with pytest.raises(ClassFlowError):
        await env.service.get_resource(result.id, env.users["rep"])


async def test_students_cannot_update_delete_or_retry(env):
    result = await upload(env)
    with pytest.raises(ClassFlowError) as caught:
        await env.service.update_resource(result.id, ResourceUpdate(title="Changed"), env.users["student"])
    assert caught.value.status_code == 403
    for operation in (env.service.delete_resource, env.service.reindex_resource):
        with pytest.raises(ClassFlowError) as caught:
            await operation(result.id, env.users["student"])
        assert caught.value.status_code == 403


async def test_update_reindexes_and_disabled_resource_can_be_reenabled_by_rep(env):
    result = await upload(env)
    result = await env.service.update_resource(result.id, ResourceUpdate(title="Updated notes"), env.users["rep"])
    assert result.title == "Updated notes"
    assert (await resource_chunks(env, result.id))[0].source_title == "Updated notes"
    result = await env.service.update_resource(result.id, ResourceUpdate(is_enabled=False), env.users["rep"])
    assert result.is_enabled is False
    assert await resource_chunks(env, result.id) == []
    assert await ResourceRepository(env.session).list_accessible_for_class(env.classroom_id, env.users["rep"]) == []
    with pytest.raises(ClassFlowError):
        await env.service.get_resource_download(result.id, env.users["student"])
    result = await env.service.update_resource(result.id, ResourceUpdate(is_enabled=True), env.users["rep"])
    assert result.indexing_status == "indexed"


async def test_metadata_update_with_embedding_failure_still_returns_saved_metadata(env):
    result = await upload(env)
    env.ai.failure = RuntimeError("unavailable")
    result = await env.service.update_resource(result.id, ResourceUpdate(title="Saved title"), env.users["rep"])
    assert result.title == "Saved title"
    assert result.indexing_status == "failed"


async def test_database_creation_failure_removes_row_and_file(env, monkeypatch):
    original = env.service.repository.create

    async def fail_after_insert(**kwargs):
        await original(**kwargs)
        raise RuntimeError("Simulated database failure")

    monkeypatch.setattr(env.service.repository, "create", fail_after_insert)
    with pytest.raises(RuntimeError):
        await upload(env)
    assert await env.session.scalar(select(func.count()).select_from(Resource).where(Resource.classroom_id == env.classroom_id)) == 0
    assert list(env.root.glob("*")) == []


async def test_partial_chunk_failure_rolls_back_chunks_and_records_failed_status(env, monkeypatch):
    original = env.rag.repository.replace_source_chunks

    async def fail_after_chunks(**kwargs):
        await original(**kwargs)
        raise RuntimeError("Simulated chunk failure")

    monkeypatch.setattr(env.rag.repository, "replace_source_chunks", fail_after_chunks)
    result = await upload(env)
    assert result.indexing_status == "failed"
    assert await resource_chunks(env, result.id) == []
    assert Path((await env.service.get_resource_download(result.id, env.users["student"])).file_path).is_file()


async def test_delete_commits_row_and_chunk_removal_before_removing_file(env):
    result = await upload(env)
    other = await upload(env, title="Other resource")
    path = Path((await env.service.get_resource_download(result.id, env.users["rep"])).file_path)
    await env.service.delete_resource(result.id, env.users["rep"])
    assert await env.session.get(Resource, result.id) is None
    assert await resource_chunks(env, result.id) == []
    assert not path.exists()
    assert len(await resource_chunks(env, other.id)) == 1


async def test_failed_delete_rolls_back_row_and_chunks_and_preserves_file(env, monkeypatch):
    result = await upload(env)
    original = env.service.repository.delete

    async def fail_after_delete(resource):
        await original(resource)
        raise RuntimeError("Simulated delete failure")

    monkeypatch.setattr(env.service.repository, "delete", fail_after_delete)
    with pytest.raises(RuntimeError):
        await env.service.delete_resource(result.id, env.users["rep"])
    assert len(await resource_chunks(env, result.id)) == 1
    assert Path((await env.service.get_resource_download(result.id, env.users["student"])).file_path).is_file()


async def test_file_cleanup_failure_is_logged_after_database_deletion(env, monkeypatch, caplog):
    result = await upload(env)
    path = Path((await env.service.get_resource_download(result.id, env.users["rep"])).file_path)
    original = Path.unlink

    def fail_for_resource(self, *args, **kwargs):
        if self == path:
            raise OSError("Simulated cleanup failure")
        return original(self, *args, **kwargs)

    monkeypatch.setattr(Path, "unlink", fail_for_resource)
    await env.service.delete_resource(result.id, env.users["rep"])
    assert await env.session.get(Resource, result.id) is None
    assert await resource_chunks(env, result.id) == []
    assert path.is_file()
    assert "Could not remove resource file" in caplog.text


async def test_course_deletion_cascades_instead_of_widening_access(env):
    result = await upload(env, course=True)
    announcement = await AnnouncementRepository(env.session).create(env.classroom_id, env.users["rep"], AnnouncementCreate(title="Scoped", body="Course only", class_course_id=env.course_id))
    announcement_id = announcement.id
    await env.session.commit()
    await env.session.execute(delete(ClassCourse).where(ClassCourse.id == env.course_id))
    await env.session.commit()
    env.session.expire_all()
    assert await env.session.scalar(select(Resource.id).where(Resource.id == result.id)) is None
    assert await env.session.scalar(select(Announcement.id).where(Announcement.id == announcement_id)) is None
    assert await resource_chunks(env, result.id) == []


async def test_announcement_repository_crud_and_pinned_order(env):
    repository = AnnouncementRepository(env.session)
    first = await repository.create(env.classroom_id, env.users["rep"], AnnouncementCreate(title="First", body="Body", is_pinned=True))
    second = await repository.create(env.classroom_id, env.users["rep"], AnnouncementCreate(title="Second", body="Body"))
    await env.session.commit()
    assert [row.id for row in await repository.list_accessible_for_class(env.classroom_id, env.users["student"])] == [first.id, second.id]
    await repository.update(first, AnnouncementUpdate(body="Updated body"))
    await env.session.commit()
    assert (await repository.get_by_id(first.id)).body == "Updated body"
    second_id = second.id
    await repository.delete(second)
    await env.session.commit()
    assert await repository.get_by_id(second_id) is None
    with pytest.raises(ClassFlowError):
        await ClassContentAccess(env.session).validate_course(env.classroom_id, env.other_course_id)


async def test_reindex_endpoint_requires_authentication_and_same_class_representative(env, monkeypatch):
    result = await upload(env)
    app = create_app()

    async def db_override():
        yield env.session

    app.dependency_overrides[get_db_session] = db_override
    monkeypatch.setattr("app.api.routes.resources.ResourceService", lambda session: env.service)
    async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://test") as client:
        url = f"/api/v1/resources/{result.id}/reindex"
        assert (await client.post(url)).status_code == 401
        for role, expected in (("student", 403), ("outsider", 404), ("rep", 200)):
            response = await client.post(url, headers={"Authorization": f"Bearer {create_access_token(str(env.users[role]))}"})
            assert response.status_code == expected
            if expected == 200:
                assert response.json()["indexing_status"] == "indexed"
                assert "storage_key" not in response.json()
