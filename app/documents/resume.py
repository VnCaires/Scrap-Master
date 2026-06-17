from __future__ import annotations

import re
import unicodedata
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
    extracted_text_path: Path | None = None
    requires_human_review: bool = True


def parse_resume_pdf(
    pdf_path: str | Path,
    max_size_mb: int = 5,
    output_text_path: str | Path | None = None,
) -> ParsedResume:
    path = Path(pdf_path)
    _validate_pdf_path(path, max_size_mb=max_size_mb)

    try:
        reader = PdfReader(path)
        pages = [page.extract_text() or "" for page in reader.pages]
    except Exception as exc:  # pypdf exposes several parser exceptions.
        raise ResumeError(f"could not read resume PDF: {path}") from exc

    raw_text = "\n".join(page.strip() for page in pages if page.strip()).strip()
    text = _normalize_extracted_text(raw_text)
    if not text:
        raise ResumeError("resume PDF did not contain extractable text")

    extracted_text_path = _write_extracted_text(text, output_text_path)

    return ParsedResume(
        pdf_path=path,
        size_bytes=path.stat().st_size,
        page_count=len(reader.pages),
        text=text,
        extracted_text_path=extracted_text_path,
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


def _write_extracted_text(text: str, output_text_path: str | Path | None) -> Path | None:
    if output_text_path is None:
        return None

    path = Path(output_text_path)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")
    return path


def _normalize_extracted_text(text: str) -> str:
    normalized = text.replace("\r\n", "\n").replace("\r", "\n").replace("\u00a0", " ")
    normalized = _fix_utf8_mojibake(normalized)
    normalized = _recompose_spacing_diacritics(normalized)
    normalized = normalized.replace("ı\u0301", "i\u0301").replace("ı\u0302", "i\u0302")
    normalized = unicodedata.normalize("NFC", normalized)
    normalized = re.sub(
        r"(?<=[A-Za-zÀ-ÿ])\s+(?=[ÃÕÁÉÍÓÚÂÊÔãõáéíóúâêô][A-Za-zÀ-ÿ]{0,2}\b)",
        "",
        normalized,
    )
    return "\n".join(line.rstrip() for line in normalized.splitlines()).strip()


def _fix_utf8_mojibake(text: str) -> str:
    best = text
    best_score = _suspicious_text_score(best)
    for _ in range(2):
        improved = False
        for encoding in ("cp1252", "latin1"):
            try:
                candidate = best.encode(encoding).decode("utf-8")
            except (UnicodeEncodeError, UnicodeDecodeError):
                continue

            candidate_score = _suspicious_text_score(candidate)
            if candidate_score < best_score:
                best = candidate
                best_score = candidate_score
                improved = True
        if not improved:
            break
    return best


def _suspicious_text_score(text: str) -> int:
    suspicious_chars = "ÂÃâË†ËœËœ€™œž¢¸˜´`^¨�"
    return sum(text.count(char) for char in suspicious_chars)


def _recompose_spacing_diacritics(text: str) -> str:
    spacing_to_combining = {
        "¸": "\u0327",
        "˜": "\u0303",
        "´": "\u0301",
        "`": "\u0300",
        "^": "\u0302",
        "ˆ": "\u0302",
        "¨": "\u0308",
    }
    output: list[str] = []
    pending_marks: list[str] = []
    length = len(text)
    index = 0

    while index < length:
        char = text[index]
        if char in spacing_to_combining:
            combining = spacing_to_combining[char]
            previous_index = _previous_non_space_index(output)
            next_index = _next_non_space_index(text, index + 1)
            if (
                combining == "\u0327"
                and previous_index is not None
                and output[previous_index] in {"c", "C"}
            ):
                output.insert(previous_index + 1, combining)
            elif next_index is not None and text[next_index].isalpha():
                pending_marks.append(combining)
            elif output and output[-1].isalpha():
                output.append(combining)
            else:
                output.append(char)
            index += 1
            continue

        if char.isspace() and pending_marks:
            next_index = _next_non_space_index(text, index + 1)
            if next_index is not None and text[next_index].isalpha():
                index += 1
                continue

        output.append(char)
        if pending_marks and char.isalpha():
            output.extend(pending_marks)
            pending_marks.clear()
        index += 1

    return "".join(output)


def _next_non_space_index(text: str, start_index: int) -> int | None:
    for index in range(start_index, len(text)):
        if not text[index].isspace():
            return index
    return None


def _previous_non_space_index(output: list[str]) -> int | None:
    for index in range(len(output) - 1, -1, -1):
        if not output[index].isspace():
            return index
    return None
