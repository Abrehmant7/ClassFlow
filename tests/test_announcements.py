"""HTTP and transactional checks for Module 6 announcements."""
import os

import pytest
from sqlalchemy import func, select

from app.core.security import create_access_token
from app.models.announcement import Announcement
from app.models.resource import RAG_SOURCE_ANNOUNCEMENT, RagChunk
from app.schemas.announcement import AnnouncementCreate, AnnouncementUpdate
from app.services.announcement import AnnouncementService

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


async def create(api, env, *, course: bool = False, pinned: bool = False, title: str = "Exam update"):
    payload = {
        "title": title,
        "body": "The exam starts at nine.",
        "is_pinned": pinned,
        "class_course_id": env.course_id if course else None,
    }
    return await api.post(
        f"/api/v1/classes/{env.classroom_id}/announcements",
        json=payload,
        headers=headers(env.users["rep"]),
    )


async def chunks(env, announcement_id: int) -> list[RagChunk]:
    return list((await env.session.scalars(select(RagChunk).where(
        RagChunk.source_type == RAG_SOURCE_ANNOUNCEMENT,
        RagChunk.source_id == announcement_id,
    ))).all())


async def test_announcement_http_crud_keeps_rag_index_in_sync(api, env):
    response = await create(api, env, course=True)
    assert response.status_code == 201
    created = response.json()
    assert created["can_manage"] is True
    assert created["class_course_id"] == env.course_id

    indexed = await chunks(env, created["id"])
    assert len(indexed) == 1
    assert indexed[0].source_title == "Exam update"
    assert "The exam starts at nine." in indexed[0].content

    response = await api.patch(
        f"/api/v1/announcements/{created['id']}",
        json={"title": "Pinned exam update", "body": "The exam starts at ten.", "is_pinned": True},
        headers=headers(env.users["rep"]),
    )
    assert response.status_code == 200
    assert response.json()["is_pinned"] is True
    indexed = await chunks(env, created["id"])
    assert len(indexed) == 1
    assert indexed[0].source_title == "Pinned exam update"
    assert "starts at ten" in indexed[0].content

    response = await api.delete(
        f"/api/v1/announcements/{created['id']}",
        headers=headers(env.users["rep"]),
    )
    assert response.status_code == 204
    assert await env.session.get(Announcement, created["id"]) is None
    assert await chunks(env, created["id"]) == []


async def test_announcement_lists_are_ordered_and_filtered_by_scope(api, env):
    classwide = (await create(api, env, title="Classwide")).json()
    course = (await create(api, env, course=True, pinned=True, title="Course pinned")).json()

    expected = {
        "rep": [course["id"], classwide["id"]],
        "student": [course["id"], classwide["id"]],
        "unregistered": [classwide["id"]],
    }
    for role, ids in expected.items():
        response = await api.get(
            f"/api/v1/classes/{env.classroom_id}/announcements",
            headers=headers(env.users[role]),
        )
        assert response.status_code == 200
        assert [item["id"] for item in response.json()] == ids
        assert all(item["can_manage"] is (role == "rep") for item in response.json())

    for role in ("pending", "removed", "outsider"):
        response = await api.get(
            f"/api/v1/classes/{env.classroom_id}/announcements",
            headers=headers(env.users[role]),
        )
        assert response.status_code == 404


async def test_announcement_exact_id_access_and_management_do_not_leak(api, env):
    announcement = (await create(api, env, course=True)).json()
    url = f"/api/v1/announcements/{announcement['id']}"

    assert (await api.get(url)).status_code == 401
    assert (await api.get(url, headers=headers(env.users["student"]))).status_code == 200
    assert (await api.get(url, headers=headers(env.users["unregistered"]))).status_code == 404
    assert (await api.get(url, headers=headers(env.users["outsider"]))).status_code == 404
    assert (await api.patch(url, json={"title": "No"}, headers=headers(env.users["student"]))).status_code == 403
    assert (await api.delete(url, headers=headers(env.users["student"]))).status_code == 403


async def test_announcement_validation_and_course_scope_errors_are_safe(api, env):
    base = f"/api/v1/classes/{env.classroom_id}/announcements"
    assert (await api.post(base, json={"title": "A", "body": "B"})).status_code == 401
    assert (await api.post(
        base,
        json={"title": "A", "body": "B"},
        headers=headers(env.users["student"]),
    )).status_code == 403
    assert (await api.post(
        base,
        json={"title": "A", "body": "B", "class_course_id": env.other_course_id},
        headers=headers(env.users["rep"]),
    )).status_code == 404

    created = (await create(api, env)).json()
    response = await api.patch(
        f"/api/v1/announcements/{created['id']}",
        json={"title": None},
        headers=headers(env.users["rep"]),
    )
    assert response.status_code == 422
    assert response.json()["error_code"] == "VALIDATION_ERROR"


async def test_announcement_indexing_failure_rolls_back_create_and_update(env):
    service = AnnouncementService(env.session, rag_service=env.rag)
    env.ai.failure = RuntimeError("provider unavailable")
    with pytest.raises(RuntimeError):
        await service.create_announcement(
            env.classroom_id,
            AnnouncementCreate(title="Will roll back", body="Body"),
            env.users["rep"],
        )
    assert await env.session.scalar(select(func.count()).select_from(Announcement).where(
        Announcement.classroom_id == env.classroom_id,
    )) == 0

    env.ai.failure = None
    created = await service.create_announcement(
        env.classroom_id,
        AnnouncementCreate(title="Original", body="Original body"),
        env.users["rep"],
    )
    env.ai.failure = RuntimeError("provider unavailable")
    with pytest.raises(RuntimeError):
        await service.update_announcement(
            created.id,
            AnnouncementUpdate(title="Should not persist"),
            env.users["rep"],
        )
    env.session.expire_all()
    saved = await env.session.get(Announcement, created.id)
    assert saved.title == "Original"
    assert (await chunks(env, created.id))[0].source_title == "Original"


@pytest.mark.parametrize("role,visible", [
    ("rep", True),
    ("student", True),
    ("unregistered", False),
    ("pending", False),
    ("removed", False),
    ("outsider", False),
])
async def test_course_announcement_rag_visibility_includes_unregistered_representative(env, role, visible):
    service = AnnouncementService(env.session, rag_service=env.rag)
    announcement = await service.create_announcement(
        env.classroom_id,
        AnnouncementCreate(title="Course notice", body="Only course readers", class_course_id=env.course_id),
        env.users["rep"],
    )
    matches = await env.rag.repository.search_accessible(
        env.classroom_id,
        env.users[role],
        [0.1] * 768,
        5,
        0.8,
    )
    assert (announcement.id in {match.chunk.source_id for match in matches}) is visible
