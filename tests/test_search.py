from datetime import datetime, timedelta, timezone
from uuid import uuid4

import pytest

from app.core.security import create_access_token
from app.models.announcement import Announcement
from app.models.resource import Resource
from app.models.task import Task


@pytest.fixture
def anyio_backend():
    return "asyncio"


def headers(user_id: int) -> dict[str, str]:
    return {"Authorization": f"Bearer {create_access_token(str(user_id))}"}


@pytest.fixture
async def searchable_content(env):
    marker = uuid4().hex[:10]
    now = datetime.now(timezone.utc)
    rows = [
        Task(
            classroom_id=env.classroom_id,
            created_by_user_id=env.users["rep"],
            title=f"Database {marker} task",
            description=f"Normalization exercise {marker}",
            task_type="assignment",
            visibility="shared",
            priority="high",
            status="active",
            deadline=now + timedelta(days=2),
        ),
        Task(
            classroom_id=env.classroom_id,
            class_course_id=env.course_id,
            created_by_user_id=env.users["rep"],
            title=f"Course-only {marker}",
            description=f"Registered course material {marker}",
            task_type="quiz",
            visibility="shared",
            priority="urgent",
            status="active",
            deadline=now + timedelta(days=3),
        ),
        Task(
            created_by_user_id=env.users["rep"],
            title=f"Private {marker}",
            description=f"Private notes {marker}",
            task_type="other",
            visibility="personal",
            priority="low",
            status="active",
        ),
        Announcement(
            classroom_id=env.classroom_id,
            created_by_user_id=env.users["rep"],
            title=f"Announcement {marker}",
            body=f"Important timetable body {marker}",
        ),
        Resource(
            classroom_id=env.classroom_id,
            class_course_id=env.course_id,
            uploaded_by_user_id=env.users["rep"],
            title=f"Lecture {marker}",
            description=f"Database resource description {marker}",
            file_name="search.pdf",
            storage_key=f"tests/{marker}.pdf",
            content_type="application/pdf",
            file_size=10,
            checksum_sha256="a" * 64,
            is_enabled=True,
            indexing_status="indexed",
        ),
    ]
    env.session.add_all(rows)
    await env.session.commit()
    return marker, rows


@pytest.mark.anyio
async def test_search_finds_all_supported_content_and_applies_task_filters(env, api, searchable_content):
    marker, rows = searchable_content
    student_headers = headers(env.users["student"])

    for query, expected_type in (
        (f"Database {marker} task", "task"),
        (f"Normalization exercise {marker}", "task"),
        (f"Announcement {marker}", "announcement"),
        (f"timetable body {marker}", "announcement"),
        (f"Lecture {marker}", "resource"),
        (f"resource description {marker}", "resource"),
    ):
        response = await api.get("/api/v1/search", params={"q": query}, headers=student_headers)
        assert response.status_code == 200
        assert expected_type in {item["entity_type"] for item in response.json()["items"]}

    filtered = await api.get(
        "/api/v1/search",
        params={
            "q": marker,
            "entity_type": "task",
            "classroom_id": env.classroom_id,
            "class_course_id": env.course_id,
            "task_type": "quiz",
            "priority": "urgent",
            "status": "active",
            "date_from": (datetime.now(timezone.utc) + timedelta(days=1)).date().isoformat(),
            "date_to": (datetime.now(timezone.utc) + timedelta(days=4)).date().isoformat(),
        },
        headers=student_headers,
    )
    assert filtered.status_code == 200
    assert [item["id"] for item in filtered.json()["items"]] == [rows[1].id]


@pytest.mark.anyio
async def test_search_never_exposes_private_or_unauthorized_course_content(env, api, searchable_content):
    marker, rows = searchable_content
    student = await api.get("/api/v1/search", params={"q": f"Private {marker}"}, headers=headers(env.users["student"]))
    assert student.status_code == 200 and student.json()["items"] == []

    unregistered = await api.get("/api/v1/search", params={"q": marker}, headers=headers(env.users["unregistered"]))
    ids = {(item["entity_type"], item["id"]) for item in unregistered.json()["items"]}
    assert ("task", rows[1].id) not in ids
    assert ("resource", rows[4].id) not in ids
    assert ("task", rows[0].id) in ids

    pending = await api.get(
        "/api/v1/search",
        params={"q": marker, "classroom_id": env.classroom_id},
        headers=headers(env.users["pending"]),
    )
    assert pending.status_code == 403
    course_filter = await api.get(
        "/api/v1/search",
        params={"q": marker, "class_course_id": env.course_id},
        headers=headers(env.users["unregistered"]),
    )
    assert course_filter.status_code == 403
