"""Shared transaction-isolated Module 6 integration fixtures."""
from io import BytesIO
import os
from pathlib import Path
import shutil
from types import SimpleNamespace
from uuid import uuid4

import httpx
from pypdf import PdfWriter
from pypdf.generic import DecodedStreamObject, DictionaryObject, NameObject
import pytest
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.pool import NullPool

from app.core.config import settings
from app.database.session import get_db_session
from app.main import create_app
from app.models.classroom import ClassMembership, Classroom
from app.models.course import ClassCourse, Course, CourseRegistration
from app.models.user import User
from app.services.announcement import AnnouncementService
from app.services.rag import RagChatService
from app.services.resource import ResourceService


class FakeEmbeddings:
    failure = None

    async def embed_documents(self, chunks, title=None):
        if self.failure:
            raise self.failure
        return [[0.1] * 768 for _ in chunks]


def small_pdf():
    writer = PdfWriter()
    page = writer.add_blank_page(width=612, height=792)
    font = DictionaryObject({
        NameObject("/Type"): NameObject("/Font"),
        NameObject("/Subtype"): NameObject("/Type1"),
        NameObject("/BaseFont"): NameObject("/Helvetica"),
    })
    page[NameObject("/Resources")] = DictionaryObject({
        NameObject("/Font"): DictionaryObject({NameObject("/F1"): writer._add_object(font)}),
    })
    content = DecodedStreamObject()
    content.set_data(b"BT /F1 12 Tf 72 720 Td (Module six course material and assignment instructions.) Tj ET")
    page[NameObject("/Contents")] = writer._add_object(content)
    output = BytesIO()
    writer.write(output)
    return output.getvalue()


@pytest.fixture
async def env(monkeypatch):
    if not os.getenv("CLASSFLOW_TEST_DATABASE_URL"):
        pytest.skip("Set CLASSFLOW_TEST_DATABASE_URL for PostgreSQL integration checks")
    allowed = (Path.cwd() / ".pytest_cache" / "module6_integration").resolve()
    root = allowed / uuid4().hex
    monkeypatch.setattr(settings, "COURSE_RESOURCE_STORAGE_DIR", str(root))
    engine = create_async_engine(os.environ["CLASSFLOW_TEST_DATABASE_URL"], poolclass=NullPool)
    try:
        async with engine.connect() as connection:
            transaction = await connection.begin()
            try:
                async with AsyncSession(bind=connection, expire_on_commit=False, join_transaction_mode="create_savepoint") as session:
                    suffix = uuid4().hex
                    users = {}
                    for role in ("rep", "student", "unregistered", "pending", "removed", "outsider"):
                        user = User(username=f"m6-{role}-{suffix}", email=f"{role}-{suffix}@example.com", password_hash="unused")
                        session.add(user)
                        users[role] = user
                    await session.flush()
                    classroom = Classroom(name="Module 6 test", semester=1, section="A", join_code=suffix[:12], creator_id=users["rep"].id)
                    other_class = Classroom(name="Other test class", semester=1, section="B", join_code=suffix[-12:], creator_id=users["rep"].id)
                    course = Course(name=f"Module 6 {suffix}", code=suffix)
                    session.add_all([classroom, other_class, course])
                    await session.flush()
                    memberships = {}
                    for role, user in users.items():
                        if role == "outsider":
                            continue
                        membership = ClassMembership(
                            user_id=user.id,
                            classroom_id=classroom.id,
                            role="representative" if role == "rep" else "student",
                            status=role if role in {"pending", "removed"} else "approved",
                        )
                        session.add(membership)
                        memberships[role] = membership
                    class_course = ClassCourse(classroom_id=classroom.id, course_id=course.id, created_by_user_id=users["rep"].id)
                    other_course = ClassCourse(classroom_id=other_class.id, course_id=course.id, created_by_user_id=users["rep"].id)
                    session.add_all([class_course, other_course])
                    await session.flush()
                    session.add(CourseRegistration(membership_id=memberships["student"].id, class_course_id=class_course.id))
                    await session.commit()
                    ai = FakeEmbeddings()
                    rag = RagChatService(session, ai_client=ai)
                    yield SimpleNamespace(
                        session=session, root=root, users={role: user.id for role, user in users.items()},
                        classroom_id=classroom.id, other_classroom_id=other_class.id, course_id=class_course.id, other_course_id=other_course.id,
                        ai=ai, rag=rag, service=ResourceService(session, rag_service=rag), pdf=small_pdf(),
                    )
            finally:
                await transaction.rollback()
    finally:
        await engine.dispose()
        if allowed in root.resolve().parents:
            shutil.rmtree(root, ignore_errors=True)


@pytest.fixture
async def api(env, monkeypatch):
    app = create_app()

    async def db_override():
        yield env.session

    app.dependency_overrides[get_db_session] = db_override
    monkeypatch.setattr("app.api.routes.resources.ResourceService", lambda session: env.service)
    monkeypatch.setattr(
        "app.api.routes.announcements.AnnouncementService",
        lambda session, **kwargs: AnnouncementService(session, rag_service=env.rag),
    )
    async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://test") as client:
        yield client
