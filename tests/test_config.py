from pathlib import Path

import pytest

from app.config.settings import load_profile, load_settings


def test_load_settings_example() -> None:
    settings = load_settings("config/settings.example.yaml")

    assert settings.llm.provider == "mock"
    assert settings.runtime.require_human_review is True
    assert settings.security.allow_auto_submit is False
    assert settings.enabled_sources()[0].name == "mock"
    assert settings.profile_path.as_posix() == "config/profile.yaml"


def test_environment_overrides_database_url(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("SCRAP_MASTER_DATABASE_URL", "sqlite:///tmp/test.db")

    settings = load_settings("config/settings.example.yaml")

    assert settings.storage.database_url == "sqlite:///tmp/test.db"


def test_rejects_auto_submit_override(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("SCRAP_MASTER_ALLOW_AUTO_SUBMIT", "true")

    with pytest.raises(ValueError, match="auto-submit"):
        load_settings("config/settings.example.yaml")


def test_load_profile_example() -> None:
    profile = load_profile(Path("config/profile.example.yaml"))

    assert profile.personal.first_name == "Vinicius"
    assert "Python" in profile.experience.skills


def test_profile_reports_fields_requiring_review() -> None:
    profile = load_profile(Path("config/profile.example.yaml"))

    assert "answers.salary_expectation" in profile.fields_requiring_review()
