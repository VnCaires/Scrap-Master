from typer.testing import CliRunner
from sqlmodel import Session, select

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
            "tests/fixtures/job_form.html",
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
