from pathlib import Path

import pytest
from pypdf import PdfWriter
from pypdf.generic import DecodedStreamObject, DictionaryObject, NameObject

from app.documents import ResumeError, parse_resume_pdf
from app.documents.resume import _normalize_extracted_text


def test_parse_resume_pdf_extracts_text(tmp_path: Path) -> None:
    pdf_path = tmp_path / "resume.pdf"
    _write_pdf_with_text(pdf_path, "Python LLM Resume")

    parsed = parse_resume_pdf(pdf_path)

    assert parsed.page_count == 1
    assert "Python" in parsed.text


def test_parse_resume_pdf_writes_extracted_text(tmp_path: Path) -> None:
    pdf_path = tmp_path / "resume.pdf"
    output_path = tmp_path / "output" / "resume.txt"
    _write_pdf_with_text(pdf_path, "Python LLM Resume")

    parsed = parse_resume_pdf(pdf_path, output_text_path=output_path)

    assert parsed.extracted_text_path == output_path
    assert "Python" in output_path.read_text(encoding="utf-8")


def test_normalize_extracted_text_fixes_brazilian_mojibake_and_diacritics() -> None:
    broken = "Cientista da ComputaÂ¸ cËœ ao\n+55 71 â€” Salvador\nInglË† es\nFORMAC Â¸ÃƒO"

    normalized = _normalize_extracted_text(broken)

    assert "Computação" in normalized
    assert "—" in normalized
    assert "Inglês" in normalized
    assert "FORMAÇÃO" in normalized


def test_parse_resume_pdf_rejects_missing_file(tmp_path: Path) -> None:
    with pytest.raises(ResumeError, match="not found"):
        parse_resume_pdf(tmp_path / "missing.pdf")


def test_parse_resume_pdf_rejects_non_pdf_extension(tmp_path: Path) -> None:
    text_path = tmp_path / "resume.txt"
    text_path.write_text("not a pdf", encoding="utf-8")

    with pytest.raises(ResumeError, match=".pdf"):
        parse_resume_pdf(text_path)


def test_parse_resume_pdf_rejects_large_file(tmp_path: Path) -> None:
    pdf_path = tmp_path / "resume.pdf"
    pdf_path.write_bytes(b"0" * 2048)

    with pytest.raises(ResumeError, match="too large"):
        parse_resume_pdf(pdf_path, max_size_mb=0)


def _write_pdf_with_text(path: Path, text: str) -> None:
    writer = PdfWriter()
    page = writer.add_blank_page(width=612, height=792)
    stream = DecodedStreamObject()
    stream.set_data(f"BT /F1 12 Tf 72 720 Td ({text}) Tj ET".encode("utf-8"))
    page[NameObject("/Contents")] = writer._add_object(stream)
    page[NameObject("/Resources")] = DictionaryObject(
        {
            NameObject("/Font"): DictionaryObject(
                {
                    NameObject("/F1"): writer._add_object(
                        DictionaryObject(
                            {
                                NameObject("/Type"): NameObject("/Font"),
                                NameObject("/Subtype"): NameObject("/Type1"),
                                NameObject("/BaseFont"): NameObject("/Helvetica"),
                            }
                        )
                    )
                }
            )
        }
    )
    with path.open("wb") as handle:
        writer.write(handle)
