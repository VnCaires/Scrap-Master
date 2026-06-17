import json

from typer.testing import CliRunner
from sqlmodel import Session, select
import yaml

from app.browser import BrowserAutomationError, inspect_form_page
from app.cli.main import app
from app.storage import ApplicationAttemptRecord, create_db_engine
from tests.helpers import write_settings


def test_cli_help() -> None:
    result = CliRunner().invoke(app, ["--help"])

    assert result.exit_code == 0
    assert "Scrap Master" in result.output


def test_cli_search_uses_mock_source() -> None:
    result = CliRunner().invoke(
        app,
        ["search", "--settings", "config/settings.example.yaml", "--keyword", "Python", "--limit", "1"],
    )

    assert result.exit_code == 0
    assert "Python" in result.output


def test_cli_init_db_search_rank_and_run(tmp_path) -> None:
    settings = write_settings(tmp_path)
    runner = CliRunner()

    init_result = runner.invoke(app, ["init-db", "--settings", str(settings)])
    search_result = runner.invoke(
        app,
        ["search", "--settings", str(settings), "--keyword", "Python LLM", "--limit", "2"],
    )
    rank_result = runner.invoke(
        app,
        ["rank", "--settings", str(settings), "--keyword", "Python LLM"],
    )
    run_result = runner.invoke(
        app,
        ["run", "--settings", str(settings), "--keyword", "Python LLM", "--limit", "2"],
    )

    assert init_result.exit_code == 0
    assert search_result.exit_code == 0
    assert "Saved" in search_result.output
    assert rank_result.exit_code == 0
    assert "Created" in rank_result.output
    assert run_result.exit_code == 0
    assert "Browser automation is not implemented yet" in run_result.output


def test_cli_inspect_form_and_review(tmp_path) -> None:
    import asyncio
    import pytest

    try:
        asyncio.run(inspect_form_page("tests/fixtures/job_form.html", headless=True))
    except BrowserAutomationError as exc:
        pytest.skip(str(exc))

    settings = write_settings(tmp_path)
    runner = CliRunner()

    inspect_result = runner.invoke(
        app,
        [
            "inspect-form",
            "--settings",
            str(settings),
            "--url",
            "tests/fixtures/job_form.html",
        ],
    )
    review_result = runner.invoke(
        app,
        [
            "review",
            "--settings",
            str(settings),
            "--url",
            "tests/fixtures/job_apply.html",
            "--decision",
            "approve",
        ],
    )

    assert inspect_result.exit_code == 0
    assert "resume" in inspect_result.output
    assert review_result.exit_code == 0
    assert "No submit action was performed" in review_result.output

    engine = create_db_engine(f"sqlite:///{tmp_path / 'scrap_master.db'}")
    with Session(engine) as session:
        attempts = session.exec(select(ApplicationAttemptRecord)).all()

    assert len(attempts) == 1
    assert attempts[0].status == "approved"
    assert attempts[0].submitted_at is None
    result_payload = json.loads(attempts[0].result_json or "{}")
    assert result_payload["submitted"] is False
    assert result_payload["resume_attached"] is True
    assert result_payload["attached_files"]

    attempts_result = runner.invoke(
        app,
        [
            "attempts",
            "--settings",
            str(settings),
        ],
    )
    attempt_show_result = runner.invoke(
        app,
        [
            "attempt-show",
            "1",
            "--settings",
            str(settings),
        ],
    )

    assert attempts_result.exit_code == 0
    assert "#1" in attempts_result.output
    assert "approved" in attempts_result.output
    assert attempt_show_result.exit_code == 0
    assert "Application attempt #1" in attempt_show_result.output
    assert '"submitted": false' in attempt_show_result.output


def test_cli_inspect_flow(tmp_path) -> None:
    import asyncio
    import pytest

    try:
        asyncio.run(inspect_form_page("tests/fixtures/job_apply.html", headless=True))
    except BrowserAutomationError as exc:
        pytest.skip(str(exc))

    settings = write_settings(tmp_path)
    runner = CliRunner()

    result = runner.invoke(
        app,
        [
            "inspect-flow",
            "--settings",
            str(settings),
            "--url",
            "tests/fixtures/careers_home.html",
        ],
    )

    assert result.exit_code == 0
    assert "Visited pages: 3" in result.output
    assert "Page type: apply_form" in result.output
    assert "job_apply.html" in result.output


def test_cli_parse_resume_writes_output(tmp_path) -> None:
    from tests.helpers import write_pdf_with_text

    runner = CliRunner()
    resume = tmp_path / "resume.pdf"
    output = tmp_path / "resume_parsed.txt"
    write_pdf_with_text(resume, "Python LLM Resume")

    result = runner.invoke(
        app,
        [
            "parse-resume",
            "--pdf",
            str(resume),
            "--output",
            str(output),
        ],
    )

    assert result.exit_code == 0
    assert "Extracted text saved:" in result.output
    assert "Python" in output.read_text(encoding="utf-8")


def test_cli_fill_form(tmp_path) -> None:
    import asyncio
    import pytest

    try:
        asyncio.run(inspect_form_page("tests/fixtures/job_form.html", headless=True))
    except BrowserAutomationError as exc:
        pytest.skip(str(exc))

    settings = write_settings(tmp_path)
    runner = CliRunner()

    result = runner.invoke(
        app,
        [
            "fill-form",
            "--settings",
            str(settings),
            "--url",
            "tests/fixtures/job_apply.html",
            "--screenshot",
            str(tmp_path / "filled-form.png"),
        ],
    )

    assert result.exit_code == 0
    assert "Filled fields:" in result.output
    assert "Pending review fields:" in result.output
    assert "No submit action was performed" in result.output

    engine = create_db_engine(f"sqlite:///{tmp_path / 'scrap_master.db'}")
    with Session(engine) as session:
        attempts = session.exec(select(ApplicationAttemptRecord)).all()

    assert len(attempts) == 1
    assert attempts[0].status == "needs_review"
    assert attempts[0].submitted_at is None


def test_cli_review_rejects_missing_resume(tmp_path) -> None:
    import asyncio
    import pytest

    try:
        asyncio.run(inspect_form_page("tests/fixtures/job_form.html", headless=True))
    except BrowserAutomationError as exc:
        pytest.skip(str(exc))

    settings = write_settings(tmp_path)
    settings_data = yaml.safe_load(settings.read_text(encoding="utf-8"))
    settings_data["resume_pdf_path"] = str(tmp_path / "missing.pdf")
    settings.write_text(yaml.safe_dump(settings_data), encoding="utf-8")

    result = CliRunner().invoke(
        app,
        [
            "review",
            "--settings",
            str(settings),
            "--url",
            "tests/fixtures/job_form.html",
            "--decision",
            "approve",
        ],
    )

    assert result.exit_code == 1
    assert "Resume error:" in result.output
