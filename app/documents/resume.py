from __future__ import annotations

from pathlib import Path

from pydantic import BaseModel, Field
from pypdf import PdfReader


class ResumeError(ValueError):
    """Raised when a resume PDF cannot be validated or parsed."""


class ParsedResume(BaseModel):
    pdf_path: Path
    size_bytes: int = Field(ge=0)
    page_count: int = Field(ge=0)
    text: str
    requires_human_review: bool = True


def parse_resume_pdf(pdf_path: str | Path, max_size_mb: int = 5) -> ParsedResume:
    path = Path(pdf_path)
    _validate_pdf_path(path, max_size_mb=max_size_mb)

    try:
        reader = PdfReader(path)
        pages = [page.extract_text() or "" for page in reader.pages]
    except Exception as exc:  # pypdf exposes several parser exceptions.
        raise ResumeError(f"could not read resume PDF: {path}") from exc

    text = "\n".join(page.strip() for page in pages if page.strip()).strip()
    if not text:
        raise ResumeError("resume PDF did not contain extractable text")

    return ParsedResume(
        pdf_path=path,
        size_bytes=path.stat().st_size,
        page_count=len(reader.pages),
        text=text,
    )


def _validate_pdf_path(path: Path, max_size_mb: int) -> None:
    if not path.exists():
        raise ResumeError(f"resume PDF not found: {path}")
    if not path.is_file():
        raise ResumeError(f"resume path is not a file: {path}")
    if path.suffix.lower() != ".pdf":
        raise ResumeError("resume file must use the .pdf extension")

    max_size_bytes = max_size_mb * 1024 * 1024
    size_bytes = path.stat().st_size
    if size_bytes > max_size_bytes:
        raise ResumeError(
            f"resume PDF is too large: {size_bytes} bytes exceeds {max_size_bytes} bytes"
        )
