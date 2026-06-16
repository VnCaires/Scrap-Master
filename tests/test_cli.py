from typer.testing import CliRunner

from app.cli.main import app


def test_cli_help() -> None:
    result = CliRunner().invoke(app, ["--help"])

    assert result.exit_code == 0
    assert "AutoApply LLM" in result.output


def test_cli_search_uses_mock_source() -> None:
    result = CliRunner().invoke(app, ["search", "--keyword", "Python", "--limit", "1"])

    assert result.exit_code == 0
    assert "Python" in result.output
