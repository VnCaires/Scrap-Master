import asyncio
from pathlib import Path

import pytest

from app.browser import (
    BrowserAutomationError,
    apply_reviewed_form_page,
    fill_form_page,
    inspect_form_page,
)
from app.config.settings import load_profile
from app.forms import map_form_fields
from tests.helpers import write_pdf_with_text


def test_fill_form_page_only_fills_safe_fields() -> None:
    profile = load_profile("config/profile.example.yaml")
    fixture = Path("tests/fixtures/job_form.html")

    try:
        inspection = asyncio.run(inspect_form_page(fixture, headless=True))
        mapping = map_form_fields(
            inspection,
            profile=profile,
            resume_pdf_path="data/input/resume.pdf",
        )
        result = asyncio.run(fill_form_page(fixture, mapping.fields, headless=True))
    except BrowserAutomationError as exc:
        pytest.skip(str(exc))

    filled_ids = {field.field_id for field in result.filled_fields}
    pending_ids = {field.field_id for field in result.pending_review_fields}

    assert {"full_name", "email", "phone", "city"}.issubset(filled_ids)
    assert "salary_expectation" in pending_ids
    assert "resume" in pending_ids
    assert result.submitted is False


def test_apply_reviewed_form_attaches_resume_without_submit(tmp_path: Path) -> None:
    profile = load_profile("config/profile.example.yaml")
    fixture = Path("tests/fixtures/job_form.html")
    resume = tmp_path / "resume.pdf"
    write_pdf_with_text(resume, "Python LLM Resume")

    try:
        inspection = asyncio.run(inspect_form_page(fixture, headless=True))
        mapping = map_form_fields(
            inspection,
            profile=profile,
            resume_pdf_path=str(resume),
        )
        result = asyncio.run(
            apply_reviewed_form_page(
                fixture,
                mapping.fields,
                resume_pdf_path=resume,
                headless=True,
            )
        )
    except BrowserAutomationError as exc:
        pytest.skip(str(exc))

    assert str(resume) in result.attached_files
    assert result.submitted is False
