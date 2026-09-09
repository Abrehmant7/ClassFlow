from dataclasses import dataclass
from io import BytesIO
from pathlib import Path

from docx import Document
from docx.table import Table
from docx.text.paragraph import Paragraph
from pypdf import PdfReader

from app.core.config import settings

SUPPORTED_RAG_ATTACHMENT_EXTENSIONS = {"pdf", "docx", "txt"}


class DocumentExtractionError(ValueError):
    pass


class DocumentTooLargeError(DocumentExtractionError):
    pass


@dataclass(frozen=True)
class ExtractedSection:
    text: str
    page_number: int | None = None


def extract_document_sections(
    file_name: str,
    file_bytes: bytes,
    max_pages: int | None = None,
    max_characters: int | None = None,
) -> list[ExtractedSection]:
    extension = Path(file_name).suffix.lower().lstrip(".")
    if extension not in SUPPORTED_RAG_ATTACHMENT_EXTENSIONS:
        return []

    page_limit = max_pages or settings.RAG_MAX_DOCUMENT_PAGES
    character_limit = max_characters or settings.RAG_MAX_EXTRACTED_CHARACTERS

    try:
        if extension == "pdf":
            sections = _extract_pdf(file_bytes, page_limit)
        elif extension == "docx":
            sections = _extract_docx(file_bytes)
        else:
            sections = _extract_text(file_bytes)
    except DocumentExtractionError:
        raise
    except Exception as exc:
        raise DocumentExtractionError("The attachment text could not be extracted") from exc

    extracted_characters = sum(len(section.text) for section in sections)
    if extracted_characters == 0:
        raise DocumentExtractionError("The attachment contains no extractable text")
    if extracted_characters > character_limit:
        raise DocumentTooLargeError("The document contains too much text to process")
    return sections


def _extract_pdf(file_bytes: bytes, max_pages: int) -> list[ExtractedSection]:
    reader = PdfReader(BytesIO(file_bytes), strict=False)
    if reader.is_encrypted:
        try:
            if not reader.decrypt(""):
                raise DocumentExtractionError("Password-protected PDFs cannot be indexed")
        except DocumentExtractionError:
            raise
        except Exception as exc:
            raise DocumentExtractionError("Password-protected PDFs cannot be indexed") from exc

    if len(reader.pages) > max_pages:
        raise DocumentTooLargeError("The PDF has too many pages to process")

    sections: list[ExtractedSection] = []
    for page_number, page in enumerate(reader.pages, start=1):
        text = (page.extract_text() or "").strip()
        if text:
            sections.append(ExtractedSection(text=text, page_number=page_number))
    return sections


def _extract_docx(file_bytes: bytes) -> list[ExtractedSection]:
    document = Document(BytesIO(file_bytes))
    blocks: list[str] = []

    for item in document.iter_inner_content():
        if isinstance(item, Paragraph):
            text = item.text.strip()
            if text:
                blocks.append(text)
        elif isinstance(item, Table):
            for row in item.rows:
                cells = [cell.text.strip() for cell in row.cells]
                row_text = " | ".join(cell for cell in cells if cell)
                if row_text:
                    blocks.append(row_text)

    text = "\n".join(blocks)
    return [ExtractedSection(text=text)] if text else []


def _extract_text(file_bytes: bytes) -> list[ExtractedSection]:
    try:
        text = file_bytes.decode("utf-8-sig").strip()
    except UnicodeDecodeError as exc:
        raise DocumentExtractionError("Text attachments must use UTF-8 encoding") from exc
    return [ExtractedSection(text=text)] if text else []
