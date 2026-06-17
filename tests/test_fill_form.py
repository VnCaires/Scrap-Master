import asyncio
from pathlib import Path

import pytest

from app.browser import BrowserAutomationError, fill_form_page, inspect_form_page
from app.config.settings import load_profile
from app.forms import map_form_fields


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
