from dataclasses import dataclass
from hashlib import sha256
import logging
import os
from pathlib import Path
from tempfile import NamedTemporaryFile
import unicodedata
from uuid import uuid4

from fastapi import UploadFile, status

from app.core.config import settings
from app.core.exceptions import ClassFlowError

logger = logging.getLogger(__name__)
UPLOAD_CHUNK_SIZE = 64 * 1024


def resource_storage_root() -> Path:
    return Path(settings.COURSE_RESOURCE_STORAGE_DIR).resolve()


def resource_file_path(storage_key: str) -> Path:
    root = resource_storage_root()
    # Treat both separator conventions as paths on every deployment platform.
    key = Path(storage_key.replace("\\", "/"))
    path = (root / key).resolve()
    if not storage_key or key.is_absolute() or ":" in storage_key or root not in path.parents:
        raise ClassFlowError("Invalid resource storage key", "INVALID_RESOURCE_STORAGE_KEY", status.HTTP_500_INTERNAL_SERVER_ERROR)
    return path


def remove_resource_file(path: Path) -> None:
    try:
        path.unlink(missing_ok=True)
    except OSError:
        logger.warning("Could not remove resource file %s", path.name)


@dataclass(frozen=True)
class StoredResource:
    file_name: str
    storage_key: str
    content_type: str
    file_size: int
    checksum_sha256: str


async def store_resource_pdf(file: UploadFile) -> StoredResource:
    name = unicodedata.normalize("NFKC", file.filename or "").replace("\\", "/").rsplit("/", 1)[-1]
    name = "".join(character for character in name if unicodedata.category(character)[0] != "C").strip()
    if not name or len(name) > 255 or Path(name).suffix.lower() != ".pdf":
        raise ClassFlowError("A PDF filename is required", "RESOURCE_EXTENSION_NOT_ALLOWED", status.HTTP_422_UNPROCESSABLE_CONTENT)
    if "pdf" not in settings.COURSE_RESOURCE_ALLOWED_EXTENSIONS:
        raise ClassFlowError("PDF uploads are disabled", "RESOURCE_EXTENSION_NOT_ALLOWED", status.HTTP_422_UNPROCESSABLE_CONTENT)
    if file.content_type != "application/pdf" or file.content_type not in settings.COURSE_RESOURCE_ALLOWED_CONTENT_TYPES:
        raise ClassFlowError("PDF content type is required", "RESOURCE_CONTENT_TYPE_NOT_ALLOWED", status.HTTP_422_UNPROCESSABLE_CONTENT)

    storage_key = f"{uuid4().hex}.pdf"
    destination = resource_file_path(storage_key)
    temporary_path: Path | None = None
    checksum = sha256()
    size = 0
    header = bytearray()
    try:
        destination.parent.mkdir(parents=True, exist_ok=True)
        # Same filesystem as the destination so os.replace is atomic.
        with NamedTemporaryFile(dir=destination.parent, prefix=".upload-", suffix=".tmp", delete=False) as output:
            temporary_path = Path(output.name)
            while True:
                chunk = await file.read(min(UPLOAD_CHUNK_SIZE, settings.COURSE_RESOURCE_MAX_SIZE_BYTES - size + 1))
                if not chunk:
                    break
                size += len(chunk)
                if size > settings.COURSE_RESOURCE_MAX_SIZE_BYTES:
                    raise ClassFlowError("Resource file is too large", "RESOURCE_TOO_LARGE", status.HTTP_413_CONTENT_TOO_LARGE)
                if len(header) < 1024:
                    header.extend(chunk[: 1024 - len(header)])
                checksum.update(chunk)
                output.write(chunk)

        if size == 0:
            raise ClassFlowError("Resource file is empty", "RESOURCE_EMPTY", status.HTTP_422_UNPROCESSABLE_CONTENT)
        if b"%PDF-" not in header:
            raise ClassFlowError("The file does not contain a PDF header", "RESOURCE_INVALID_PDF", status.HTTP_422_UNPROCESSABLE_CONTENT)
        os.replace(temporary_path, destination)
    except OSError as exc:
        raise ClassFlowError("Could not store resource file", "RESOURCE_STORAGE_FAILED", status.HTTP_500_INTERNAL_SERVER_ERROR) from exc
    finally:
        if temporary_path is not None:
            remove_resource_file(temporary_path)

    return StoredResource(name, storage_key, "application/pdf", size, checksum.hexdigest())
