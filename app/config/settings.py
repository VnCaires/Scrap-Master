from __future__ import annotations

import os
from pathlib import Path
from typing import Any

import yaml
from pydantic import BaseModel, ConfigDict, EmailStr, Field, SecretStr, field_validator

from app.core.models import JobSource


class LLMSettings(BaseModel):
    provider: str = "mock"
    model: str = "gpt-4.1-mini"
    temperature: float = Field(default=0.1, ge=0.0, le=2.0)
    api_key: SecretStr | None = None
    base_url: str | None = None

    @field_validator("provider")
    @classmethod
    def supported_provider(cls, value: str) -> str:
        if value not in {"mock", "openai_compatible"}:
            raise ValueError("llm.provider must be 'mock' or 'openai_compatible'")
        return value


class RuntimeSettings(BaseModel):
    headless: bool = False
    max_jobs_per_source: int = Field(default=20, ge=1)
    max_applications_per_run: int = Field(default=3, ge=0)
    require_human_review: bool = True
    screenshot_on_error: bool = True

    @field_validator("require_human_review")
    @classmethod
    def review_required_for_initial_version(cls, value: bool) -> bool:
        if not value:
            raise ValueError("human review must remain enabled in the initial version")
        return value


class StorageSettings(BaseModel):
    database_url: str = "sqlite:///data/scrap_master.db"


class SecuritySettings(BaseModel):
    allow_auto_submit: bool = False
    allowed_domains: list[str] = Field(default_factory=list)
    blocked_domains: list[str] = Field(default_factory=list)

    @field_validator("allow_auto_submit")
    @classmethod
    def auto_submit_is_disabled_for_initial_version(cls, value: bool) -> bool:
        if value:
            raise ValueError("auto-submit is disabled in the initial version")
        return value


class AppSettings(BaseModel):
    model_config = ConfigDict(extra="forbid")

    llm: LLMSettings = Field(default_factory=LLMSettings)
    runtime: RuntimeSettings = Field(default_factory=RuntimeSettings)
    storage: StorageSettings = Field(default_factory=StorageSettings)
    security: SecuritySettings = Field(default_factory=SecuritySettings)
    sources: list[JobSource] = Field(default_factory=lambda: [JobSource(name="mock")])
    profile_path: Path = Path("config/profile.yaml")
    resume_pdf_path: Path = Path("data/input/resume.pdf")

    def enabled_sources(self) -> list[JobSource]:
        return [source for source in self.sources if source.enabled]


class PersonalInfo(BaseModel):
    first_name: str
    last_name: str
    email: EmailStr
    phone: str = ""
    city: str = ""
    country: str = ""
    linkedin: str = ""
    github: str = ""
    portfolio: str = ""


class Preferences(BaseModel):
    target_roles: list[str] = Field(default_factory=list)
    keywords: list[str] = Field(default_factory=list)
    remote_only: bool = True
    relocation: bool = False
    contract_types: list[str] = Field(default_factory=list)
    minimum_salary: int | None = None


class Experience(BaseModel):
    years_total: int | None = Field(default=None, ge=0)
    seniority: str | None = None
    skills: list[str] = Field(default_factory=list)
    languages: dict[str, str] = Field(default_factory=dict)


class ProfileAnswers(BaseModel):
    work_authorization: str = ""
    salary_expectation: str = ""
    notice_period: str = ""
    cover_letter_template: str = ""


class UserProfile(BaseModel):
    personal: PersonalInfo
    preferences: Preferences = Field(default_factory=Preferences)
    experience: Experience = Field(default_factory=Experience)
    answers: ProfileAnswers = Field(default_factory=ProfileAnswers)

    def fields_requiring_review(self) -> list[str]:
        fields: list[str] = []
        if not self.personal.phone:
            fields.append("personal.phone")
        if not self.answers.work_authorization:
            fields.append("answers.work_authorization")
        if not self.answers.salary_expectation:
            fields.append("answers.salary_expectation")
        if not self.answers.notice_period:
            fields.append("answers.notice_period")
        if not self.answers.cover_letter_template:
            fields.append("answers.cover_letter_template")
        return fields


def load_settings(path: str | Path = "config/settings.yaml") -> AppSettings:
    data = _load_yaml(path)
    data = _deep_merge(data, _settings_from_env())
    return AppSettings.model_validate(data)


def load_profile(path: str | Path = "config/profile.yaml") -> UserProfile:
    data = _load_yaml(path)
    return UserProfile.model_validate(data)


def _load_yaml(path: str | Path) -> dict[str, Any]:
    config_path = Path(path)
    if not config_path.exists():
        raise FileNotFoundError(f"configuration file not found: {config_path}")

    with config_path.open("r", encoding="utf-8") as handle:
        loaded = yaml.safe_load(handle) or {}

    if not isinstance(loaded, dict):
        raise ValueError(f"configuration file must contain a YAML object: {config_path}")
    return loaded


def _settings_from_env() -> dict[str, Any]:
    env: dict[str, Any] = {}

    llm_env = {
        "provider": os.getenv("LLM_PROVIDER"),
        "model": os.getenv("LLM_MODEL"),
        "api_key": os.getenv("LLM_API_KEY"),
        "base_url": os.getenv("LLM_BASE_URL"),
    }
    llm_values = {key: value for key, value in llm_env.items() if value not in (None, "")}
    if llm_values:
        env["llm"] = llm_values

    storage_database_url = os.getenv("SCRAP_MASTER_DATABASE_URL")
    if storage_database_url:
        env["storage"] = {"database_url": storage_database_url}

    runtime_values: dict[str, Any] = {}
    _set_bool_env(runtime_values, "headless", "SCRAP_MASTER_HEADLESS")
    _set_bool_env(runtime_values, "require_human_review", "SCRAP_MASTER_REQUIRE_HUMAN_REVIEW")
    if runtime_values:
        env["runtime"] = runtime_values

    security_values: dict[str, Any] = {}
    _set_bool_env(security_values, "allow_auto_submit", "SCRAP_MASTER_ALLOW_AUTO_SUBMIT")
    if security_values:
        env["security"] = security_values

    return env


def _set_bool_env(target: dict[str, Any], key: str, env_name: str) -> None:
    value = os.getenv(env_name)
    if value is not None:
        target[key] = _parse_bool(value)


def _parse_bool(value: str) -> bool:
    normalized = value.strip().lower()
    if normalized in {"1", "true", "yes", "y", "on"}:
        return True
    if normalized in {"0", "false", "no", "n", "off"}:
        return False
    raise ValueError(f"invalid boolean value: {value}")


def _deep_merge(base: dict[str, Any], overrides: dict[str, Any]) -> dict[str, Any]:
    merged = dict(base)
    for key, value in overrides.items():
        if isinstance(value, dict) and isinstance(merged.get(key), dict):
            merged[key] = _deep_merge(merged[key], value)
        else:
            merged[key] = value
    return merged
