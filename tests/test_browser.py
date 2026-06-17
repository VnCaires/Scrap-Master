import asyncio
from pathlib import Path

import pytest

from app.browser import BrowserAutomationError, inspect_form_flow, inspect_form_page


def test_inspect_form_page_detects_local_fixture_fields() -> None:
    fixture = Path("tests/fixtures/job_form.html")

    try:
        inspection = asyncio.run(inspect_form_page(fixture, headless=True))
    except BrowserAutomationError as exc:
        pytest.skip(str(exc))

    field_ids = {field.field_id for field in inspection.fields}
    assert "email" in field_ids
    assert "resume" in field_ids
    assert "terms" in field_ids
    assert inspection.submit_button_selector == "#submit_application"
    assert inspection.submitted is False


def test_inspect_form_flow_navigates_local_portal() -> None:
    fixture = Path("tests/fixtures/careers_home.html")

    try:
        inspection = asyncio.run(inspect_form_flow(fixture, headless=True))
    except BrowserAutomationError as exc:
        pytest.skip(str(exc))

    field_ids = {field.field_id for field in inspection.fields}
    assert inspection.page_type == "apply_form"
    assert len(inspection.visited_pages) == 3
    assert any("job_detail.html" in visited for visited in inspection.visited_pages)
    assert any("job_apply.html" in visited for visited in inspection.visited_pages)
    assert "contact_email" in field_ids
    assert "resume_upload" in field_ids
