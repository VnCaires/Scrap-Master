from typer.testing import CliRunner

from app.cli.main import app
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
