from hashlib import sha256
from io import BytesIO
from pathlib import Path
import shutil
from uuid import uuid4

from fastapi import UploadFile
from pydantic import ValidationError
import pytest
from starlette.datastructures import Headers

from app.core.config import settings
from app.core.exceptions import ClassFlowError
from app.schemas.announcement import AnnouncementCreate, AnnouncementUpdate
from app.schemas.resource import ResourceDownload, ResourceUpdate
from app.services.resource_storage import resource_file_path, store_resource_pdf


@pytest.fixture
def anyio_backend():
    return "asyncio"


@pytest.fixture
def resource_storage(monkeypatch):
    allowed = (Path.cwd() / ".pytest_cache" / "resource_storage").resolve()
    root = allowed / uuid4().hex
    monkeypatch.setattr(settings, "COURSE_RESOURCE_STORAGE_DIR", str(root))
    yield root
    resolved = root.resolve()
    if allowed in resolved.parents:
        shutil.rmtree(resolved, ignore_errors=True)


def make_upload(name="notes.pdf", content_type="application/pdf", content=b"%PDF-1.7\nexample"):
    return UploadFile(filename=name, file=BytesIO(content), headers=Headers({"content-type": content_type}))


@pytest.mark.anyio
async def test_upload_normalizes_display_name_and_generates_private_storage_key(resource_storage):
    content = b"%PDF-1.7\n" + b"x" * 100_000
    upload = make_upload("C:\\fakepath\\notes.PDF", content=content)
    try:
        stored = await store_resource_pdf(upload)
    finally:
        await upload.close()
    assert stored.file_name == "notes.PDF"
    assert len(stored.storage_key) == 36
    assert stored.storage_key != stored.file_name
    assert stored.file_size == len(content)
    assert stored.checksum_sha256 == sha256(content).hexdigest()
    assert (resource_storage / stored.storage_key).read_bytes() == content
    assert list(resource_storage.glob("*.tmp")) == []


@pytest.mark.anyio
@pytest.mark.parametrize("name,mime,content,error", [
    ("notes.txt", "application/pdf", b"%PDF-test", "RESOURCE_EXTENSION_NOT_ALLOWED"),
    ("notes.pdf", "text/plain", b"%PDF-test", "RESOURCE_CONTENT_TYPE_NOT_ALLOWED"),
    ("notes.pdf", "application/pdf", b"<html>not a PDF</html>", "RESOURCE_INVALID_PDF"),
    ("notes.pdf", "application/pdf", b"", "RESOURCE_EMPTY"),
    ("notes.pdf", "application/pdf", b"x" * 1024 + b"%PDF-", "RESOURCE_INVALID_PDF"),
])
async def test_invalid_uploads_leave_no_files(resource_storage, name, mime, content, error):
    upload = make_upload(name, mime, content)
    try:
        with pytest.raises(ClassFlowError) as caught:
            await store_resource_pdf(upload)
    finally:
        await upload.close()
    assert caught.value.detail["error_code"] == error
    assert list(resource_storage.glob("*")) == []


@pytest.mark.anyio
async def test_oversized_stream_stops_at_limit_plus_one_and_cleans_up(resource_storage, monkeypatch):
    monkeypatch.setattr(settings, "COURSE_RESOURCE_MAX_SIZE_BYTES", 70_000)
    upload = make_upload(content=b"%PDF-1.7\n" + b"x" * 200_000)
    upload.size = 1  # Client metadata must not override the streamed byte count.
    try:
        with pytest.raises(ClassFlowError) as caught:
            await store_resource_pdf(upload)
        assert caught.value.status_code == 413
        assert upload.file.tell() == 70_001
    finally:
        await upload.close()
    assert list(resource_storage.glob("*")) == []


@pytest.mark.parametrize("key", ["../outside.pdf", "..\\outside.pdf", "/etc/file.pdf", "C:\\private.pdf", ""])
def test_storage_key_cannot_escape_private_directory(resource_storage, key):
    with pytest.raises(ClassFlowError):
        resource_file_path(key)


def test_download_descriptor_does_not_serialize_server_path():
    download = ResourceDownload(file_path="/private/course_resources/file.pdf", file_name="file.pdf", content_type="application/pdf")
    assert "file_path" not in download.model_dump()
    assert "/private/" not in repr(download)


@pytest.mark.parametrize("schema,values", [
    (AnnouncementCreate, {"title": " ", "body": "Body"}),
    (AnnouncementCreate, {"title": "Title", "body": " "}),
    (AnnouncementUpdate, {"title": None}),
    (AnnouncementUpdate, {"body": None}),
    (AnnouncementUpdate, {"is_pinned": None}),
    (ResourceUpdate, {"title": None}),
    (ResourceUpdate, {"is_enabled": None}),
    (ResourceUpdate, {"storage_key": "other.pdf"}),
])
def test_schemas_reject_invalid_updates(schema, values):
    with pytest.raises(ValidationError):
        schema(**values)
