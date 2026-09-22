"""HTTP checks for private resource upload, access, and management routes."""
import os
from pathlib import Path

import pytest
from sqlalchemy import func, select

from app.core.security import create_access_token
from app.models.resource import RAG_SOURCE_RESOURCE, Resource

pytestmark = [
    pytest.mark.anyio,
    pytest.mark.skipif(
        not os.getenv("CLASSFLOW_TEST_DATABASE_URL"),
        reason="Set CLASSFLOW_TEST_DATABASE_URL for PostgreSQL integration checks",
    ),
]


@pytest.fixture
def anyio_backend():
    return "asyncio"


def headers(user_id: int) -> dict[str, str]:
    return {"Authorization": f"Bearer {create_access_token(str(user_id))}"}


async def upload(api, env, *, role: str = "rep", course: bool = False, title: str = "Lecture notes", content=None):
    data = {"title": title, "description": "Week one material"}
    if course:
        data["class_course_id"] = str(env.course_id)
    return await api.post(
        f"/api/v1/classes/{env.classroom_id}/resources",
        data=data,
        files={"file": ("lecture.pdf", env.pdf if content is None else content, "application/pdf")},
        headers=headers(env.users[role]),
    )


async def test_resource_http_crud_and_private_download(api, env):
    response = await upload(api, env, course=True)
    assert response.status_code == 201
    resource = response.json()
    assert resource["indexing_status"] == "indexed"
    assert resource["can_manage"] is True
    assert not {"file_path", "storage_key", "checksum_sha256"} & resource.keys()

    response = await api.get(
        f"/api/v1/resources/{resource['id']}/download",
        headers=headers(env.users["student"]),
    )
    assert response.status_code == 200
    assert response.content == env.pdf
    assert response.headers["content-type"].startswith("application/pdf")
    assert response.headers["cache-control"] == "private, no-store"
    assert response.headers["x-content-type-options"] == "nosniff"
    assert "attachment" in response.headers["content-disposition"]

    response = await api.patch(
        f"/api/v1/resources/{resource['id']}",
        json={"title": "Revised lecture notes"},
        headers=headers(env.users["rep"]),
    )
    assert response.status_code == 200
    assert response.json()["title"] == "Revised lecture notes"
    assert response.json()["indexing_status"] == "indexed"

    stored = await env.session.get(Resource, resource["id"])
    path = env.root / stored.storage_key
    assert path.is_file()
    response = await api.delete(
        f"/api/v1/resources/{resource['id']}",
        headers=headers(env.users["rep"]),
    )
    assert response.status_code == 204
    assert await env.session.get(Resource, resource["id"]) is None
    assert not path.exists()


async def test_resource_scope_filters_lists_and_exact_ids(api, env):
    classwide = (await upload(api, env, title="Classwide")).json()
    course = (await upload(api, env, course=True, title="Course")).json()

    expected = {
        "rep": {classwide["id"], course["id"]},
        "student": {classwide["id"], course["id"]},
        "unregistered": {classwide["id"]},
    }
    for role, ids in expected.items():
        response = await api.get(
            f"/api/v1/classes/{env.classroom_id}/resources",
            headers=headers(env.users[role]),
        )
        assert response.status_code == 200
        assert {item["id"] for item in response.json()} == ids

    course_url = f"/api/v1/resources/{course['id']}"
    assert (await api.get(course_url)).status_code == 401
    assert (await api.get(course_url, headers=headers(env.users["unregistered"]))).status_code == 404
    assert (await api.get(course_url, headers=headers(env.users["outsider"]))).status_code == 404
    assert (await api.get(f"{course_url}/download", headers=headers(env.users["outsider"]))).status_code == 404
    assert (await api.patch(course_url, json={"title": "No"}, headers=headers(env.users["student"]))).status_code == 403
    assert (await api.delete(course_url, headers=headers(env.users["student"]))).status_code == 403

    for role in ("pending", "removed", "outsider"):
        response = await api.get(
            f"/api/v1/classes/{env.classroom_id}/resources",
            headers=headers(env.users[role]),
        )
        assert response.status_code == 404


@pytest.mark.parametrize("name,mime,content,expected", [
    ("notes.txt", "application/pdf", b"%PDF-1.7\ntext", 422),
    ("notes.pdf", "text/plain", b"%PDF-1.7\ntext", 422),
    ("notes.pdf", "application/pdf", b"not a pdf", 422),
    ("notes.pdf", "application/pdf", b"", 422),
])
async def test_resource_http_rejects_invalid_uploads_without_artifacts(api, env, name, mime, content, expected):
    response = await api.post(
        f"/api/v1/classes/{env.classroom_id}/resources",
        data={"title": "Invalid upload"},
        files={"file": (name, content, mime)},
        headers=headers(env.users["rep"]),
    )
    assert response.status_code == expected
    assert await env.session.scalar(select(func.count()).select_from(Resource).where(
        Resource.classroom_id == env.classroom_id,
    )) == 0
    assert not env.root.exists() or list(env.root.iterdir()) == []


async def test_resource_upload_auth_role_course_and_request_validation(api, env):
    url = f"/api/v1/classes/{env.classroom_id}/resources"
    files = {"file": ("lecture.pdf", env.pdf, "application/pdf")}
    assert (await api.post(url, data={"title": "A"}, files=files)).status_code == 401
    assert (await upload(api, env, role="student")).status_code == 403

    response = await api.post(
        url,
        data={"title": "A", "class_course_id": str(env.other_course_id)},
        files={"file": ("lecture.pdf", env.pdf, "application/pdf")},
        headers=headers(env.users["rep"]),
    )
    assert response.status_code == 404
    response = await api.post(
        url,
        data={"title": "   "},
        files={"file": ("lecture.pdf", env.pdf, "application/pdf")},
        headers=headers(env.users["rep"]),
    )
    assert response.status_code == 422
    assert response.json()["error_code"] == "VALIDATION_ERROR"


async def test_failed_resource_index_can_download_and_reindex(api, env):
    env.ai.failure = RuntimeError("secret/provider/detail")
    response = await upload(api, env)
    assert response.status_code == 201
    resource = response.json()
    assert resource["indexing_status"] == "failed"
    assert "secret" not in resource["indexing_error"]

    download = await api.get(
        f"/api/v1/resources/{resource['id']}/download",
        headers=headers(env.users["student"]),
    )
    assert download.status_code == 200
    assert download.content == env.pdf

    env.ai.failure = None
    response = await api.post(
        f"/api/v1/resources/{resource['id']}/reindex",
        headers=headers(env.users["rep"]),
    )
    assert response.status_code == 200
    assert response.json()["indexing_status"] == "indexed"


async def test_course_resource_rag_visibility_includes_unregistered_representative(api, env):
    resource = (await upload(api, env, course=True)).json()
    expected = {
        "rep": True,
        "student": True,
        "unregistered": False,
        "pending": False,
        "removed": False,
        "outsider": False,
    }
    for role, visible in expected.items():
        matches = await env.rag.repository.search_accessible(
            env.classroom_id,
            env.users[role],
            [0.1] * 768,
            5,
            0.8,
        )
        source_ids = {
            match.chunk.source_id
            for match in matches
            if match.chunk.source_type == RAG_SOURCE_RESOURCE
        }
        assert (resource["id"] in source_ids) is visible


async def test_disabled_resource_is_hidden_but_representative_can_restore_it(api, env):
    resource = (await upload(api, env)).json()
    url = f"/api/v1/resources/{resource['id']}"
    response = await api.patch(url, json={"is_enabled": False}, headers=headers(env.users["rep"]))
    assert response.status_code == 200
    assert response.json()["is_enabled"] is False
    assert (await api.get(url, headers=headers(env.users["student"]))).status_code == 404
    assert (await api.post(f"{url}/reindex", headers=headers(env.users["rep"]))).status_code == 409

    response = await api.patch(url, json={"is_enabled": True}, headers=headers(env.users["rep"]))
    assert response.status_code == 200
    assert response.json()["indexing_status"] == "indexed"
    assert Path((await env.service.get_resource_download(resource["id"], env.users["student"])).file_path).is_file()
